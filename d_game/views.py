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


@daily_activity
def puzzle(request):

    puzzle = Puzzle.objects.get(id=request.GET.get('p'))

    if request.user.is_authenticated():
        player_name = request.user.username
    else:
        player_name = game_master.ANON_PLAYER_NAME
    enemy_name = "ai"

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
    enemy_name = "ai"

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

    if request.user.is_authenticated():
        player_name = request.user.username
    else:
        player_name = game_master.ANON_PLAYER_NAME 

    # turn init
    game_master.heal(game, player_name) 

    # logging.info("^^^ %s hand before draw %s" % (player_name, get_player(game, player_name)['hand']))

    game_master.draw_up_to(game, player_name, 5)

    # logging.info("^^^ %s hand after draw %s" % (player_name, get_player(game, player_name)['hand']))

    player_moves = request.POST.get("player_turn").strip().split('\n')
    game_master.do_turn(game, player_name, player_moves)

    # if board.match.winner:
    # player has won. yaaaaay!!
    # return HttpResponse("") 

    game_before_ai = simplejson.dumps(game) 

    # let the computer play its turn
    game_master.heal(game, 'ai') 
    # logging.info("^^^ %s hand before draw %s" % ('ai', get_player(game, 'ai')['hand'] ))
    game_master.draw_up_to(game, 'ai', 5)

    # logging.info("^^^ %s hand after draw %s" % ('ai', get_player(game, 'ai')['hand']))
    ai_turn = ai.get_turn(game, 'ai') 
    ai_moves = [ ai_turn[0]['shorthand'], ai_turn[1]['shorthand'] ]
    game_master.do_turn(game, 'ai', ai_moves)

    game_after_ai = simplejson.dumps(game)

    #get 2 new cards for player 
    draw_cards = game_master.draw_up_to(game, player_name, 5)


    # save turn changes on server
    cached.save(game)

    #serialize and ship it
    hand_and_turn_json = """{
            'player_draw': %s,
            'ai_turn': %s,
            'verify_board_state_before_ai': %s,
            'verify_board_state_after_ai': %s,
            }""" % (simplejson.dumps(draw_cards),
                    simplejson.dumps(ai_turn),
                    game_before_ai,
                    game_after_ai)

    # logging.info(hand_and_turn_json);

    return HttpResponse(hand_and_turn_json, "application/javascript")


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
        logging.info("_______ added starting unit to ai board")

    # save changes
    cached.save(game)

    logging.info(simplejson.dumps(game))

    for card in hand:
        logging.info("5678 hand card: %s" % card)

    censored = game_master.get_censored(game, player_name)

    return HttpResponse(simplejson.dumps(censored), "application/javascript")


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

    # censor it so sensitive information about enemy's hands
    # and both players' decks is hidden from player
    censored = game_master.get_censored(game, player_name)
    game_json = simplejson.dumps(censored) 

    hand_and_turn_json = """{
            'player_draw': %s,
            'ai_turn': { },
            }""" % simplejson.dumps(hand)

    logging.info(hand_and_turn_json);

    return HttpResponse(hand_and_turn_json, "application/javascript")
