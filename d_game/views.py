import logging
import simplejson
from random import random

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.core import serializers
from django.template import RequestContext
from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.db import SessionStore

from d_board.models import Node
from d_cards.models import Card, Deck
from d_game.models import Match, Puzzle, PuzzleStartingUnit
from d_game.util import daily_activity
from d_cards.util import get_deck_from
from d_feedback.models import PuzzleFeedbackForm
from d_metrics.models import UserMetrics

from d_users.util import has_permissions_for

from d_game import cached
from d_game import game_master, ai


def log(request, match_id=None):

    if match_id:
        match = Match.objects.get(id=match_id)
    else:
        match = Match.objects.all()[Match.objects.count()-1]
    return render_to_response("match_log.html", locals()) 


@daily_activity
def puzzle(request):

    puzzle = Puzzle.objects.get(id=request.GET.get('p'))

    if request.user.is_authenticated():
        player_name = request.user.username
    else:
        player_name = game_master.ANON_PLAYER_NAME
    opponent_name = "ai"

    # check perms
    if not has_permissions_for(puzzle, request.user, request.session.session_key):
        return HttpResponseRedirect('/puzzles/')

    puzzles = Puzzle.objects.filter(state="approved")

    i = 0
    for p in puzzles:
        if p == puzzle:
            try:
                next_puzzle_url = "/puzzle/?p=%s" % puzzles[i+1].id
            except:
                next_puzzle_url = "/" 
            break
        i += 1 

    request.session["puzzle"] = puzzle.id

    match = init_puzzle_match(request, puzzle) 
    request.session["match"] = match.id

    board = Node.objects.all().order_by('-pk')

    form = PuzzleFeedbackForm()

    return render_to_response("playing.html", locals(), context_instance=RequestContext(request))

@daily_activity
def playing(request): 

    if request.user.is_authenticated():
        player_name = request.user.username
    else:
        player_name = game_master.ANON_PLAYER_NAME
    opponent_name = "ai"

    # init
    match = init_match(request) 
    request.session["match"] = match.id

    board = Node.objects.all().order_by('-pk')


    return render_to_response("playing.html", locals(), context_instance=RequestContext(request))


def init_puzzle_match(request, puzzle):

    deck = puzzle.player_cards 

    if request.user.is_authenticated():
        player = request.user
    else:
        player = None

    match = Match(type="puzzle",
            player=player,
            puzzle=puzzle,
            goal=puzzle.goal,
            session_key=request.session.session_key,
            friendly_deck_cards=puzzle.player_cards.card_ids,
            ai_deck_cards=[],
            ai_life=puzzle.ai_life,
            friendly_life=puzzle.player_life)
    match.save()

    return match 


def init_match(request):

    deck = get_deck_from(request)

    ai_deck = Deck.objects.all()[0]

    if request.user.is_authenticated():
        player = request.user
    else:
        player = None

    match = Match(friendly_deck_cards=deck.card_ids,
            ai_deck_cards=ai_deck.card_ids,
            player=player,
            type="ai")
    match.save()

    return match 


def end_turn(request):

    # grab game info
    match_id = request.session['match'] 
    game = cached.get_game(match_id) 

    # get player's actions from requests
    player_moves = request.POST.get("player_turn").strip().split('\n')
    if not player_moves:
        player_moves = ["pass %s" % game['player'], "pass %s" % game['player']] 

    # process the game turn and get data to give back to client
    hand_and_turn_json = game_master.do_turns(game, player_moves) 

    logging.info("))))) end turn, did do_turns")

    # did the game end this turn?
    winner = game_master.is_game_over(game)
    logging.info("))))) end turn, winner? %s" % winner)
    if winner:
        match = Match.objects.get(id=match_id)
        logging.info("))))) trying to set winner: %s for %s" % (winner, match.puzzle))
        if match.puzzle:
            if request.user.is_authenticated():
                request.user.get_profile().beaten_puzzle_ids.append(match.puzzle.id)
                request.user.get_profile().save()
        match.winner = winner 

        return HttpResponse("game over, winner: %s" % winner)

    # send appropriate hand & AI info back to client
    return HttpResponse(hand_and_turn_json, "application/javascript")




def first_turn(request):

    match = Match.objects.get(id=request.session["match"])

    if match.type == "ai":
        return begin_ai_game(request)

    elif match.type == "puzzle":
        return begin_puzzle_game(request) 


def begin_ai_game(request):
    
    match = Match.objects.get(id=request.session["match"])
    game = cached.get_game(match.id)

    if request.user.is_authenticated():
        player_name = request.user.username
    else:
        player_name = game_master.ANON_PLAYER_NAME

    hand = game_master.draw_up_to(game, player_name, 5)

    cached.save(game)
    censored = game_master.get_censored(game, player_name)

    return HttpResponse(simplejson.dumps(censored), "application/javascript")


def begin_puzzle_game(request):

    match = Match.objects.get(id=request.session['match'])
    game = cached.get_game(match.id)

    if request.user.is_authenticated():
        player_name = request.user.username
    else:
        player_name = game_master.ANON_PLAYER_NAME

    hand = game_master.draw_up_to(game, player_name, 5)

    # init puzzle life
    game['players'][player_name]['life'] = match.puzzle.player_life

    # puzzle starting units
    starting_units = PuzzleStartingUnit.objects.filter(puzzle=match.puzzle)

    for starting_unit in starting_units:
        game_master.play(game, 'ai', starting_unit.unit_card.pk, 'ai', starting_unit.location.row, starting_unit.location.x, ignore_hand=True)

    cached.save(game) 
    censored = game_master.get_censored(game, player_name)

    return HttpResponse(simplejson.dumps(censored), "application/javascript")
