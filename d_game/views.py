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
from d_cards.models import Card, ShuffledLibrary, Deck
from d_game.models import Turn, Match, Board, Unit, AI, Puzzle
from d_game.util import daily_activity
from d_cards.util import get_deck_from
from d_feedback.models import PuzzleFeedbackForm
from d_metrics.models import UserMetrics

from d_users.util import has_permissions_for


@daily_activity
def puzzle(request):

    puzzle = Puzzle.objects.get(id=request.GET.get('p'))

    # check perms
    if not has_permissions_for(puzzle, request.user, request.session.session_key):
        return HttpResponseRedirect('/puzzles/')



    puzzles = Puzzle.objects.all()
    i = 0
    for p in puzzles:
        if p == puzzle:
            try:
                next_puzzle_url = "/puzzle/?p=%s" % puzzles[i+1].id
            except:
                next_puzzle_url = "/" 
            break
        i += 1 

    logging.info("** got puzzle w/ life: %s" % puzzle.player_life)
    request.session["puzzle"] = puzzle.id

    match = init_puzzle_match(request, puzzle) 
    request.session["match"] = match.id

    board = Node.objects.all().order_by('-pk')

    form = PuzzleFeedbackForm()

    return render_to_response("playing.html", locals(), context_instance=RequestContext(request))

@daily_activity
def playing(request): 

    # init
    match = init_match(request) 
    request.session["match"] = match.id

    board = Node.objects.all().order_by('-pk')


    return render_to_response("playing.html", locals(), context_instance=RequestContext(request))


def init_puzzle_match(request, puzzle):

    deck = puzzle.player_deck 
    ai_deck = None

    # don't shuffle that library! card order can be
    # important to the puzzles
    friendly_library = ShuffledLibrary().init(deck, False)
    friendly_library.save()

    #ai doesn't get a hand or library...  

    if request.user.is_authenticated():
        player = request.user
    else:
        player = None

    match = Match(type="puzzle",
            player=player,
            session_key=request.session.session_key,
            friendly_library=friendly_library,
            ai_library=None)
    match.save()

    return match 


def init_match(request):

    deck = get_deck_from(request)

    ai_deck = Deck.objects.all()[0]

    friendly_library = ShuffledLibrary().init(deck)
    friendly_library.save()
    ai_library = ShuffledLibrary().init(ai_deck)
    ai_library.save()

    # starting hand, to be filled to 5 on first AI turn
    ai_library.draw(3)

    if request.user.is_authenticated():
        player = request.user
    else:
        player = None

    match = Match(friendly_library=friendly_library,
            player=player,
            ai_library=ai_library,
            type="ai")
    match.save()

    return match 


def process_player_turn(request, board):

    # heal player's units
    board.heal("friendly")

    card = None
    node = None

    # first player cast
    node_id = request.POST.get("node1")

    if node_id == "surrender":
        logging.info("TODO: player surrender")
        return

    elif node_id == "pass":
        # do nothing. player has passed this phase
        pass

    try:
        node = Node.objects.get(id=node_id)
    except:
        # node_id could be 'pass' or 'surrender' or 'tech'...
        pass

    card_id = request.POST.get("card1")
    try:
        card = Card.objects.get(id=card_id) 
    except:
        pass

    if card and node:
        board.cast(request.POST.get("align1", "friendly"), card, node, True)
        board.match.friendly_library.play(card.id)
    elif node_id == "tech":
        board.match.friendly_tech += 1
        board.match.friendly_library.play(card.id)
        board.match.save()
    else:
        # no player action
        pass

    #attack!
    board.do_attack_phase("friendly", True)

    # second player cast
    node = None
    card = None

    node_id = request.POST.get("node2")

    if node_id == "surrender":
        logging.info("TODO: player surrender 2")
        return

    elif node_id == "pass":
        # do nothing. player has passed this phase
        pass

    try:
        node = Node.objects.get(id=node_id)
    except:
        # node_id could be 'pass' or 'surrender' or 'tech'...
        pass

    card_id = request.POST.get("card2")
    try:
        card = Card.objects.get(id=card_id) 
    except:
        pass

    if card and node:
        board.cast(request.POST.get("align2", "friendly"), card, node, True)
        board.match.friendly_library.play(card.id)
    elif node_id == "tech":
        board.match.friendly_tech += 1
        board.match.friendly_library.play(card.id)
        board.match.save()
    else:
        # no player action
        pass

    # remove player rubble
    board.remove_one_rubble("friendly")


def end_turn(request):

    board = Board()
    board.load_from_session(request.session)

    if board.match.winner:
        # someone has won. yaaaaay!!
        return HttpResponse("")

    # process what the player has just done & update board state 
    process_player_turn(request, board)

    if board.match.winner:
        # player has won. yaaaaay!!
        return HttpResponse("") 

    before_ai_board_simple_json = board.to_simple_json()

    ai_turn = AI().do_turn(board)

    #get 2 new cards for player
    logging.info("*** player hand: %s" % board.match.friendly_library.hand_card_ids)
    num_to_draw = 5 - len(board.match.friendly_library.hand_card_ids)
    draw_cards = board.match.friendly_library.draw_as_json(num_to_draw)
     
    play_cards = []
    if ai_turn.play_1:
        play_cards.append(ai_turn.play_1)
    if ai_turn.play_2:
        play_cards.append(ai_turn.play_2)

    #serialize and ship it
    hand_and_turn_json = """{
            'player_draw': %s,
            'ai_turn': %s,
            'ai_cards': %s,
            'verify_board_state_before_ai': %s,
            'verify_board_state_after_ai': %s,
            }""" % (draw_cards,
                    serializers.serialize("json", [ai_turn]),
                    serializers.serialize("json", play_cards),
                    before_ai_board_simple_json,
                    board.to_simple_json())

    logging.info(hand_and_turn_json);

    return HttpResponse(hand_and_turn_json, "application/javascript")


def begin_puzzle_game(request):

    match = Match.objects.get(id=request.session["match"])

    hand_json = match.friendly_library.draw_as_json(5)

    puzzle = Puzzle.objects.get(id=request.session["puzzle"])
    puzzle.init(match)

    ai_turn = puzzle.get_setup_turn() 

    play_cards = []
    for play in ai_turn:
        play_cards.append(Card.objects.get(id=play['card']))

    hand_and_turn_json = """{
            'player_draw': %s,
            'ai_starting_units': %s,
            'ai_cards': %s,
            }""" % (hand_json,
                    simplejson.dumps(ai_turn),
                    serializers.serialize("json", play_cards))

    return HttpResponse(hand_and_turn_json, "application/javascript")


def first_turn(request):

    match = Match.objects.get(id=request.session["match"])

    if match.type == "ai":
        return begin_ai_game(request)

    elif match.type == "puzzle":
        return begin_puzzle_game(request) 


def begin_ai_game(request):
    
    match = Match.objects.get(id=request.session["match"])

    hand_json = match.friendly_library.draw_as_json(5)

    hand_and_turn_json = """{
            'player_draw': %s,
            'ai_turn': { },
            'ai_cards': { },
            }""" % hand_json

    logging.info(hand_and_turn_json);

    return HttpResponse(hand_and_turn_json, "application/javascript")
