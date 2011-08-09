import logging

from django.core.cache import cache

from d_cards.models import Card
from d_game.models import Match


def save(game_object):

    cache.set("match_%s" % game_object['pk'], game_object)


def get_game(match_id):

    from d_game.game_master import init_game

    game = cache.get("match_%s" % match_id)
    if not game:
        match = Match.objects.get(id=match_id)
        game = init_game(match)
        cache.set("match_%s" % match.id, game)
    else:
        logging.info("12341234 got game from cache")

    return game 


def all_cards():

    cards = cache.get("all_cards")
    if cards:
        return cards

    cards = Card.objects.all()
    cache.set("all_cards", cards, 60 * 10)
    return cards


def get_card(card_id):
    try:
        return get_cards([card_id])[0]
    except:
        logging.info("!@#$ exception: couldn't find card with id= %s" % card_id)


def get_cards(card_ids):

    from django.forms.models import model_to_dict

    all = all_cards()
    cards = []

    for id in card_ids:
        for card in all:
            if card.id == int(id):
                card_obj = { 'pk': card.pk,
                        'fields': model_to_dict(card, fields=[], exclude=[]) 
                    }
                cards.append(card_obj)
                break

    return cards

