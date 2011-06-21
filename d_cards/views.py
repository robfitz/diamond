from django.template import RequestContext
from django.core import serializers
from django.shortcuts import render_to_response
from django.http import HttpResponse

from d_cards.models import Deck, Card


def edit_deck(request):

    try:
        deck = Deck.objects.all()[0]
    except:
        deck = Deck()
        deck.save()

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

    deck = Deck.objects.all()[0]
    deck.card_ids = card_ids
    deck.save()

    return HttpResponse("ok") 
