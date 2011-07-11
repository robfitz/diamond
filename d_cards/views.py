import logging

from django.template import RequestContext
from django.core import serializers
from django.shortcuts import render_to_response
from django.http import HttpResponse

from d_cards.models import Deck, Card
from d_game.models import Puzzle
from d_cards.util import get_deck_from


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
            if not puzzle.player_deck:
                d = Deck()
                d.save()
                puzzle.player_deck = d
                puzzle.save()
            deck = puzzle.player_deck 
        # and if none of the special params exist, get the
        # user's deck
        else: 
            deck = get_deck_from(request)

    # non-staff users aren't allowed to use the special deck
    # params, so just load their deck regardless
    else: 
        deck = get_deck_from(request) 

    return render_to_response("edit_deck.html", locals(), context_instance=RequestContext(request))


def get_library_cards(request):

    all_cards = Card.objects.all()

    json = serializers.serialize("json", all_cards)

    return HttpResponse(json, "application/javascript")


def save_deck(request):

    card_ids = []

    for key in request.POST: 
        if key.startswith('deck_card_'):

            card_id = request.POST.get(key)
            card_ids.append(card_id)

    deck_id = request.POST.get("deck_id")
    logging.info("**** got deck id: %s" % deck_id)
    deck = Deck.objects.get(id=deck_id)

    deck.card_ids = card_ids[:deck.max_size]
    deck.nickname = request.POST.get("nickname", "")
    deck.save()

    logging.info("*** saved deck: %s" % deck.id)

    return HttpResponse("ok") 
