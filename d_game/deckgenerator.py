import random

from d_cards.models import Card, Deck


def create_deck(max_points):

    cards = Card.objects.all()
    card_ids = []
    total = 0

    # deck builder looks for an exact point match, but will
    # up if it misses it some number of time
    overshots = 5 

    while total < max_points and overshots > 0:

        i = random.randint(0, len(cards) - 1)   

        if cards[i].card_power_level + total <= max_points:
            total += cards[i].card_power_level
            card_ids.append(cards[i].pk)
        else:
            overshots -= 1
            continue

    deck = Deck(nickname="Random AI deck",
            card_ids = card_ids,
            max_size = 100,
            max_points = max_points)
    deck.save()
    return deck









