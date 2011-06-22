import logging

from django.template import RequestContext
from django.core import serializers
from django.shortcuts import render_to_response
from django.http import HttpResponse

from d_cards.models import Deck, Card


def edit_deck(request):

    if request.GET.get("ai"):
        # ai deck is just the first one
        deck = Deck.objects.all()[0]
    else: 
        try:
            # get my deck-in-progress that i built via the editor
            deck_id = request.session["deck_id"]
            deck = Deck.objects.get(id=deck_id)
        except:
            # start me a new deck
            deck = Deck()
            deck.save()
            request.session["deck_id"] = deck.id

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
    deck = Deck.objects.get(id=deck_id)

    deck.card_ids = card_ids
    deck.save()

    return HttpResponse("ok") 
