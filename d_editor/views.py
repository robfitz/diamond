from d_cards.util import get_deck_from
from d_game.util import daily_activity 

from d_cards.models import PuzzleDeck, Deck
from d_game.models import Puzzle 
from d_board.models import Node

from django.template import RequestContext
from django.shortcuts import render_to_response


def edit_puzzle(request):

    try:
        puzzle = Puzzle.objects.get(id=request.GET.get('p'))
    except:
        # new puzzle
        puzzle = Puzzle() 

    board = Node.objects.all().order_by('-pk')

    return render_to_response("edit_puzzle.html", locals(), context_instance=RequestContext(request))


@daily_activity
def edit_deck(request):

    deck = None

    # first check for various params which cause us
    # to load special decks...
    if request.user.is_staff:
        if request.GET.get("ai"):
            # ai deck is just the first one
            deck = Deck.objects.all()[0]
        elif request.GET.get("id"):
            deck = Deck.objects.get(id=request.GET.get("id")) 
        elif request.GET.get("p"):
            puzzle = Puzzle.objects.get(id=request.GET.get("p"))
            if not puzzle.player_cards:
                d = PuzzleDeck()
                d.save()
                puzzle.player_cards = d
                puzzle.save()
            deck = puzzle.player_cards 
        # and if none of the special params exist, get the
        # user's deck
        else: 
            deck = get_deck_from(request)

    # non-staff users aren't allowed to use the special deck
    # params, so just load their deck regardless
    else: 
        deck = get_deck_from(request) 

    return render_to_response("edit_deck.html", locals(), context_instance=RequestContext(request))

