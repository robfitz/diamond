import logging
from random import random

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.core import serializers
from django.template import RequestContext

from d_board.models import Node
from d_cards.models import Card
from d_game.models import Turn

def playing(request):

    board = Node.objects.all()

    # keep current game state in the session.
    # when the board changes, we'll set
    # request.session.X_board[row][x] = unit.pk or "rubble"
    request.session["friendly_board"] = {}
    request.session["ai_board"] = {}

    return render_to_response("playing.html", locals(), context_instance=RequestContext(request))


def end_turn(request):

    logging.info("** end_turn()")

    #find any card i'm able to use
    play_1 = Card.objects.filter(tech_level=1)[0]
    play_2 = Card.objects.filter(tech_level=1)[0]

    logging.info("** chose cards to play")

    ai_board = request.session["ai_board"];
    for node in Node.objects.all():
        try:
            if ai_board[node.row][node.x] == "":
                target_node_1 = node
                break
        except KeyError:
            target_node_1 = node
            break
                
    if not target_node_1:
        target_node_1 = "tech"
    else:
        try:
            ai_board[target_node_1.row][target_node_1.x] = play_1.pk
        except KeyError:
            ai_board[target_node_1.row] = {}
            ai_board[target_node_1.row][target_node_1.x] = play_1.pk
        logging.info("** set node %s %s to: %s" % (target_node_1.row, target_node_1.x, play_1.pk))

    for node in Node.objects.all():
        try:
            if ai_board[node.row][node.x] == "":
                target_node_2 = node
                break
        except KeyError:
            target_node_2 = node
            break 

    if not target_node_2: 
        target_node_2 = "tech"
    else:
        try:
            ai_board[target_node_2.row][target_node_2.x] = play_2.pk
        except KeyError:
            ai_board[target_node_2.row] = {}
            ai_board[target_node_2.row][target_node_2.x] = play_2.pk 
        logging.info("** set node %s %s to: %s" % (target_node_2.row, target_node_2.x, play_2.pk))

    logging.info("** chose targets")

    ai_turn = Turn(play_1=play_1,
            target_node_1=target_node_1,
            target_alignment_1="friendly",
            play_2=play_2,
            target_node_2=target_node_2,
            target_alignment_2="friendly")

    logging.info("** did ai turn")
            
    #get 2 new cards for player
    deck = Card.objects.all()
    c = deck.count()
    i = random() * (deck.count() - 1)
    draw_1 = deck[int(i)]
    i = random() * (deck.count() - 1)
    draw_2 = deck[int(i)]

    logging.info("** drew cards")

    #serialize and ship it
    hand_and_turn_json = """{
            'player_draw': %s,
            'ai_turn': %s,
            'ai_cards': %s,
            }""" % (serializers.serialize("json", [draw_1, draw_2]),
                    serializers.serialize("json", [ai_turn]),
                    serializers.serialize("json", [play_1, play_2]))

    return HttpResponse(hand_and_turn_json, "application/javascript")

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
