from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.core import serializers

from d_board.models import Node
from d_cards.models import Card

def playing(request):

    board = Node.objects.all()

    return render_to_response("playing.html", locals())


def draw(request):

    # try getting current game for this user

        # exists and in progress?

            # it's time to draw. send him a filled hand

            # drawing is not a legal move now. send a fail note.

         # exists and have all ended? make one!

         # none exist? make one!

    
    hand = Card.objects.select_related().all()[:5]
    hand_json = serializers.serialize("json", hand)

    return HttpResponse(hand_json, "application/javascript") 
