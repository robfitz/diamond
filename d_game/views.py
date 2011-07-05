import logging
from random import random

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.core import serializers
from django.template import RequestContext

from d_board.models import Node
from d_cards.models import Card, ShuffledLibrary, Deck
from d_game.models import Turn, Match, Board, Unit, AI, Puzzle


def puzzle(request):

    # init

    puzzle = Puzzle.objects.get(id=request.GET.get('p'))
    logging.info("** got puzzle w/ life: %s" % puzzle.player_life)
    request.session["puzzle"] = puzzle.id

    match = init_puzzle_match(puzzle) 
    request.session["match"] = match.id

    board = Node.objects.all().order_by('-pk')

    return render_to_response("playing.html", locals(), context_instance=RequestContext(request))

def playing(request): 

    # init
    match = init_match(request) 
    request.session["match"] = match.id

    board = Node.objects.all().order_by('-pk')


    return render_to_response("playing.html", locals(), context_instance=RequestContext(request))


def init_puzzle_match(puzzle):

    deck = puzzle.player_deck 
    ai_deck = None

    # don't shuffle that library! card order can be
    # important to the puzzles
    friendly_library = ShuffledLibrary().init(deck, False)
    friendly_library.save()

    #ai doesn't get a hand or library...  

    match = Match(type="puzzle",
            friendly_library=friendly_library,
            ai_library=None)
    match.save()

    return match 


def init_match(request):

    try:
        # get my custom deck progress that i built via the editor
        deck_id = request.session.get("deck_id")
        deck = Deck.objects.get(id=deck_id)
    except:
        # start me a new deck
        deck = Deck()
        deck.save()

    ai_deck = Deck.objects.all()[0]

    friendly_library = ShuffledLibrary().init(deck)
    friendly_library.save()
    ai_library = ShuffledLibrary().init(ai_deck)
    ai_library.save()

    # starting hand, to be filled to 5 on first AI turn
    ai_library.draw(3)

    match = Match(friendly_library=friendly_library,
            ai_library=ai_library,
            type="ai")
    match.save()

    return match 


def process_player_turn(request, board):

    if request.POST.get("i_win"):
        logging.info("!! player won game !!")

    # heal player's units
    board.heal("friendly")

    card = None
    node = None

    # first player cast
    node_id = id=request.POST.get("node1")
    if node_id and node_id != "tech":
        node = Node.objects.get(id=node_id)

    card_id = request.POST.get("card1")
    if card_id:
        card = Card.objects.get(id=card_id) 
    if card and node:
        board.cast("friendly", card, node, True)
    elif node_id == "tech":
        logging.info("!! TODO: tech up friendly 1")
    else:
        logging.info("No player action 1")

    #attack!
    board.do_attack_phase("friendly", True)

    # second player cast
    node = None
    card = None

    node_id = id=request.POST.get("node2")
    if node_id and node_id != "tech":
        node = Node.objects.get(id=node_id)
    card_id = request.POST.get("card2")
    if card_id:
        card = Card.objects.get(id=card_id) 
    if card and node:
        board.cast("friendly", card, node, True)
    elif node_id == "tech":
        logging.info("!! TODO: tech up friendly 2")
    else:
        logging.info("No player action 2")


def end_turn(request):

    board = Board()
    board.load_from_session(request.session)

    # process what the player has just done & update board state 
    process_player_turn(request, board)

    before_ai_board_simple_json = board.to_simple_json()

    ai_turn = AI().do_turn(board)

    #get 2 new cards for player
    draw_cards = board.match.friendly_library.draw_as_json(2)
     
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
    logging.info("** beginnign puzzle game, got hand: %s" % hand_json)

    puzzle = Puzzle.objects.get(id=request.session["puzzle"])

    ai_turn = puzzle.get_setup_turn()

    play_cards = []
    if ai_turn.play_1:
        play_cards.append(ai_turn.play_1)
    if ai_turn.play_2:
        play_cards.append(ai_turn.play_2)

    hand_and_turn_json = """{
            'player_draw': %s,
            'ai_turn': %s,
            'ai_cards': %s,
            }""" % (hand_json,
                    serializers.serialize("json", [ai_turn]),
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
