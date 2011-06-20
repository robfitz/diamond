import logging
from random import random

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.core import serializers
from django.template import RequestContext

from d_board.models import Node
from d_cards.models import Card
from d_game.models import Turn, Match, Board, Unit

def playing(request):

    board = Node.objects.all()

    request.session.flush();

    match = Match()
    match.save()
    request.session["match"] = match.id

    return render_to_response("playing.html", locals(), context_instance=RequestContext(request))


def cast(match, board, owner_alignment, card_to_play, node_to_target):

    logging.info("** pre-cast(): played card node %s %s to: %s" % (node_to_target.row, node_to_target.x, card_to_play.pk))

    unit = Unit(card=card_to_play,
            match=match,
            owner_alignment=owner_alignment,
            row=node_to_target.row,
            x=node_to_target.x)
    unit.save()

    board.nodes[owner_alignment]["%s_%s" % (unit.row, unit.x)] = {
        'type': "unit",
        'unit': unit
    }

    logging.info("** cast(): played card node %s %s to: %s" % (node_to_target.row, node_to_target.x, card_to_play.pk))


def heal(match, alignment):

    for unit in Unit.objects.filter(match=match).filter(owner_alignment=alignment):

        unit.heal()


def end_turn(request):

    logging.info("** end_turn()")

    match = Match.objects.get(id=request.session["match"])
    logging.info("** got match: %s" % match.id)

    board = Board()
    board.load_from_session(request.session)
    board.log()

    # process what the player has just done & update board state

    if request.POST.get("i_win"):
        logging.info("!! player won game !!")

    logging.info("BOARD BEFORE PLAYER HEAL")
    board.log()

    # heal player's units
    heal(match, "friendly")

    logging.info("BOARD AFTER PLAYER HEAL")
    board.log()

    # first player cast
    node = None
    node_id = id=request.POST.get("node1")
    if node_id != "tech":
        node = Node.objects.get(id=node_id)

    card_id = request.POST.get("card1")
    card = Card.objects.get(id=card_id) 
    if node:
        cast(match, board, "friendly", card, node)
    else:
        logging.info("!! TODO: tech up friendly 1")

    logging.info("BOARD BEFORE PLAYER ATTACK (AFTER CAST 1)")
    board.log()

    #attack!
    board.do_attack_phase("friendly")

    logging.info("BOARD AFTER PLAYER ATTACK")
    board.log()

    # second player cast
    node = None
    node_id = id=request.POST.get("node2")
    if node_id != "tech":
        node = Node.objects.get(id=node_id)
    card_id = request.POST.get("card2")
    card = Card.objects.get(id=card_id) 
    if node:
        cast(match, board, "friendly", card, node)
    else:
        logging.info("!! TODO: tech up friendly 2")
    
    logging.info("BOARD AFTER PLAYER CAST 2")
    board.log()

    # ai cast
    # find any card i'm able to use
    play_1 = Card.objects.filter(tech_level=1)[0]
    play_2 = Card.objects.filter(tech_level=1)[0]

    logging.info("** chose cards to play")

    target_node_1 = None
    target_node_2 = None
    is_tech_1 = False
    is_tech_2 = False

    logging.info("BOARD BEFORE AI HEAL")
    board.log()

    #heal and attack
    heal(match, "ai")

    logging.info("BOARD AFTER AI HEAL")
    board.log()

    # ai play first card
    for row in range(3):
        if target_node_1:
            break
        for x in range(-row, row+1): 
            if not board.nodes["ai"]["%s_%s" % (row, x)]:
                target_node_1 = Node.objects.get(row=row,x=x)
                break
                
    if not target_node_1:
        logging.info("** ai 1st cast: teching")
        is_tech_1 = True
        target_node_1 = None
    else:
        cast(match, board, "ai", play_1, target_node_1)

    logging.info("BOARD AFTER AI CAST 1")
    board.log()

    board.do_attack_phase("ai")

    logging.info("BOARD AFTER AI ATTACK")
    board.log()

    # ai play second card
    for row in range(3):
        if target_node_2:
            break
        for x in range(-row, row+1): 
            if not board.nodes["ai"]["%s_%s" % (row, x)]:
                target_node_2 = Node.objects.get(row=row,x=x)
                break

    if not target_node_2: 
        logging.info("** ai 2nd cast: teching")
        is_tech_2 = True
        target_node_2 = None
    else:
        cast(match, board, "ai", play_2, target_node_2)

    logging.info("BOARD AFTER AI CAST 2")
    board.log()

    logging.info("** chose targets")

    ai_turn = Turn(play_1=play_1,
            target_node_1=target_node_1,
            is_tech_1=is_tech_1,
            target_alignment_1="friendly",
            play_2=play_2,
            target_node_2=target_node_2,
            is_tech_2=is_tech_2,
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

    logging.info(hand_and_turn_json);

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
