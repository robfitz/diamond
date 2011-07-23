import json, logging, simplejson

from d_cards.util import get_deck_from
from d_game.util import daily_activity 

from d_cards.models import PuzzleDeck, Deck, Card, ShuffledLibrary
from d_game.models import Puzzle, PuzzleStartingUnit
from d_board.models import Node

from django.template import RequestContext
from django.core import serializers
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse


@login_required
def edit_puzzle(request):

    if request.method == "POST":

        puzzle_id = request.POST.get("p") 
        logging.info("got puzzle id here we goooo: %s" % puzzle_id)

        try:
            logging.info("tryina grab puzzle")
            puzzle = Puzzle.objects.get(id=int(puzzle_id)) 
            if request.user.is_staff or request.user == puzzle.creator:
                logging.info("got it ad allowed (tryina grab puzzle")
                pass
            else:
                logging.info("not allowed")
                raise Error 

        except:
            logging.info("makin new puzz")
            puzzle = Puzzle(creator=request.user,
                    order=Puzzle.objects.all().count() + 1)

        player_life = int(request.POST.get("player_life", 1))
        ai_life = int(request.POST.get("player_life", 10))
        goal = request.POST.get("goal", "kill units")

        puzzle.player_life = player_life
        puzzle.ai_life = ai_life
        puzzle.goal = goal
        puzzle.save()

        json_str = request.POST.get("board_json")
        logging.info("getting this sweet board from json: %s" % json_str)
        board_obj = json.loads( json_str )

        for old_unit in PuzzleStartingUnit.objects.filter(puzzle=puzzle):
            old_unit.delete()

        for unit in board_obj:
            if not puzzle.id:
                puzzle.save()

            unit_id = unit["id"]
            node_id = unit["node_id"]
            node_alignment = unit["alignment"]

            card = Card.objects.get(id=unit_id)
            node = Node.objects.get(id=node_id)

            starting_unit = PuzzleStartingUnit(puzzle=puzzle,
                    owner=request.user,
                    unit_card=card,
                    location=node)

            starting_unit.save() 

        return HttpResponse("%s" % puzzle.id)

    try:
        puzzle = Puzzle.objects.get(id=request.GET.get('p'))
    except:
        # new puzzle
        puzzle = Puzzle() 

    starting_units = PuzzleStartingUnit.objects.filter(puzzle=puzzle)

    board = Node.objects.all().order_by('-pk')

    return render_to_response("edit_puzzle.html", locals(), context_instance=RequestContext(request))


@login_required
def get_puzzle_data(request):

    puzzle_id = request.GET.get('p')
    logging.info("TTT: %s" % puzzle_id)
    puzzle = Puzzle.objects.get(id=puzzle_id)
    ai_turn = puzzle.get_setup_turn() 

    friendly_library = ShuffledLibrary().init(puzzle.player_cards, False)
    deck_json = friendly_library.draw_as_json(1000)

    # TODO: creating then immediately deleting it cannot be proper...
    friendly_library.delete()

    play_cards = []
    for play in ai_turn:
        play_cards.append(Card.objects.get(id=play['card']))

    hand_and_turn_json = """{
            'player_deck': %s,
            'ai_starting_units': %s,
            'ai_cards': %s,
            }""" % (deck_json,
                    simplejson.dumps(ai_turn),
                    serializers.serialize("json", play_cards))

    return HttpResponse(hand_and_turn_json, "application/javascript") 


@daily_activity
def edit_deck(request):

    deck = None

    # first check for various params which cause us
    # to load special decks...
    if request.GET.get("ai") and request.user.is_staff:
        # ai deck is just the first one
        deck = Deck.objects.all()[0]
    elif request.GET.get("id") and request.user.is_staff:
        deck = Deck.objects.get(id=request.GET.get("id")) 
    elif request.GET.get("p"):

        puzzle = Puzzle.objects.get(id=request.GET.get("p"))

        if puzzle.can_be_edited_by(request.user): 
            if not puzzle.player_cards:
                d = PuzzleDeck()
                d.save()
                puzzle.player_cards = d
                puzzle.save()
            deck = puzzle.player_cards 

    # and if none of the special params exist, get the
    # user's deck
    if not deck: 
        logging.info("*** not deck,g etting from req")
        deck = get_deck_from(request)

    return render_to_response("edit_deck.html", locals(), context_instance=RequestContext(request))

