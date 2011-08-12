import random, logging, copy

from django.core import serializers
from d_game import cached

from django.core.cache import cache


ANON_PLAYER_NAME = "guest"

def init_game(match):

    if match.player:
        player = match.player.username
    else:
        player = ANON_PLAYER_NAME

    game = {    
            'pk': match.pk,
            'type': match.type,
            'goal': match.goal,
            'current_phase': 1,
            'current_player': player,
            'players': {
                player: {
                    'life': match.friendly_life,
                    'tech': match.friendly_tech,
                    'hand': [],
                    'library': cached.get_cards(match.friendly_deck_cards),
                    'board': { },
                },
                'ai': {
                    'life': match.ai_life,
                    'tech': match.ai_tech,
                    'hand': [],
                    'library': cached.get_cards(match.ai_deck_cards),
                    'board': { },
                }
            }
        }

    # init board
    for row in range(0, 3):
        for col in range(-row, row + 1):
            set_node(game, player, row, col, {})
            set_node(game, 'ai', row, col, {})

    # shuffle if appropriate
    if game['type'] != "puzzle":
        random.shuffle(get_player(game, player)['library'])
        random.shuffle(get_player(game, 'ai')['library'])

    return game


def get_censored(game, player):

    # avoid changing the old one
    game = copy.deepcopy(game)

    game['player'] = player

    opponent = game['players'][get_opponent_name(game, player)]

    # censor enemy hand
    opponent['hand'] = { 'length': len(opponent['hand']) }

    # censor enemy library
    opponent['library'] = { 'length': len(opponent['library']) }

    # censor own library so can't look ahead
    game['players'][player]['library'] = { 'length': len(game['players'][player]['library']) } 

    return game


def do_turn(game, player, moves, is_ai=False):

    # first play
    do_turn_move(game, player, moves[0])

    # attack!
    do_attack_phase(game, player)

    # second play
    do_turn_move(game, player, moves[1])

    # cleanup
    remove_rubble(game, player)


def do_turn_move(game, player, move):

    toks = move.split(' ')

    action = toks[1]

    if action == 'pass':
        pass

    elif action == "surrender":
        logging.info("TODO: %s surrender" % player)

    elif action == 'tech':
        card_id = toks[2]
        if discard(game, player, card_id):
            tech(game, player, 1)

    elif action == 'play':
        card_id = toks[2]
        node_owner = toks[3]
        row = toks[4]
        x = toks[5]

        play(game, player, card_id, node_owner, row, x) 


# return False if was an illegal play
def play(game, player, card_id, node_owner, row, x, ignore_hand=False):

    if not ignore_hand:
        # remove card from hand
        card = discard(game, player, card_id) 
    else:
        from d_cards.models import Card
        card = Card.objects.get(id=card_id)

        from django.forms.models import model_to_dict
        card = { 'pk': card.pk,
                'fields': model_to_dict(card, fields=[], exclude=[]) 
            }
            
    if not card:
        # fail if requested card was not in hand
        return False

    nodes = []
    if card['fields']['target_aiming'] == 'chosen': 
        nodes.append({ 'row': row, 'x': x})

    elif card['fields']['target_aiming'] == 'all': 
        for row in range(3):
            for col in range(-row, row+1): 
                if not get_board(game, node_owner)["%s_%s" % (row, col)]: 
                    nodes.append({ 'row': row, 'x': col }); 

    for node in nodes:
        # loop to support 'all node' targetting as well as 'chosen'

        if card['fields']['tech_change']:
            tech(game, player, card['fields']['tech_change'])

        if card['fields']['direct_damage']:
            # direct damage 
            target = get_board(game, player)["%s_%s" % (node["row"], node['x'])]
            if target and target['type'] == "unit":
                damage_unit(game, card['fields']['direct_damage'], target, card)

        if card['fields']['defense']: 
            # summon critter

            # add a few fields to the card to represent a unit
            card['type'] = 'unit'
            card['damage'] = 0
            card['player'] = player
            card['row'] = int(node['row'])
            card['x'] = int(node['x'])

            # deep copy in case of multiple targets for same card
            get_board(game, player)["%s_%s" % (node["row"], node["x"])] = copy.deepcopy(card)


def discard(game, player, card_id):
    i = 0
    for card in get_player(game, player)['hand']:
        if int(card['pk']) == int(card_id):
            card = get_player(game, player)['hand'][i]
            del get_player(game, player)['hand'][i]
            return card
        i += 1
    return False


def tech(game, player, amount):
    get_player(game, player)['tech'] += amount 


def draw_up_to(game, player, total):

    num = total - len(get_player(game, player)['hand'])
    return draw(game, player, num)

def draw(game, player, num):

    # remove from deck
    drawn = get_player(game, player)['library'][:num]
    del get_player(game, player)['library'][:num]

    # add to hand
    get_player(game, player)['hand'].extend(drawn)

    # return the delta
    return drawn


def do_attack_phase(game, attacking_player):

    for_each_unit(game, attacking_player, do_attack)


def do_attack(game, attacking_player, unit):

    attacked_player = get_opponent_name(game, attacking_player)

    row = int(unit['row'])
    x = int(unit['x'])

    alignment = attacking_player
    is_searching = True 
    steps_taken = 0 

    fields = unit['fields']

    if fields['attack_type'] == "na" or fields['attack_type'] == "counterattack":
        # some types of units don't do anything during an active attack
        return

    while is_searching:
        if alignment != attacking_player:
            d_row = -1
        elif row == 2:
            d_row = 0
            alignment = attacked_player
        else:
            d_row = 1

        row += d_row
        old_x = x

        if x != 0 and abs(x) > row:
            x = row * x / abs(x)

        steps_taken += 1

        if fields['attack_type'] == "flying" and steps_taken < 3:
            # flying units skip the 2 spots in front of them
            continue

        if alignment == attacking_player and fields['attack_type'] == "ranged":
            # ranged units always pass over friendly tiles, so
            # don't even worry about checking collisions
            continue

        try:
            next_node = get_board(game, alignment)["%s_%s" % (row, x)]
        except KeyError:
            next_node = None

        if next_node and next_node['type'] == "unit":
            if alignment == attacking_player:
                # bumped into friendly
                return
            elif next_node and next_node['type'] == "unit":
                # bumped into enemy unit
                is_dead = damage_unit(game, fields['attack'], next_node, unit)
                return
                
        elif row == 0 and x == 0:
            # bumped into enemy player

            if attacked_player == "ai" and game['goal'] == 'kill units':
                # in puzzle mode where trying to kill all units, AI is invulnerable
                pass
            else:
                get_player(game, attacked_player)['life'] -= fields['attack']

            return 


def get_player(game, player): 
    return game['players'][player]


def get_opponent_name(game, player): 
    for player_name in game['players']:
        if player_name != player:
            return player_name 


def get_board(game, player):
    return get_player(game, player)['board']


def get_node(game, player, row, x):
    return get_board(game, player)["%s_%s" % (row, x)]


def set_node(game, player, row, x, val):
    get_board(game, player)["%s_%s" % (row, x)] = val


def each_type(game, player, type):

    types = []

    board = get_board(game, player) 
    for row in range(0, 3):
        for col in range(-row, row + 1):
            node = get_node(game, player, row, col)
            node_type = None
            try:
                node_type = node['type']
            except KeyError:
                # blank nodes have no type
                continue
            if node and node_type == type: 
                types.append(node)

    return types 


def each_unit(game, player):

    return each_type(game, player, 'unit')



def for_each_unit(game, player, callback):

    for_each_type(game, player, "unit", callback)


def for_each_type(game, player, type, callback):

    board = get_board(game, player) 
    for row in range(0, 3):
        for col in range(-row, row + 1):
            node = get_node(game, player, row, col)
            node_type = None
            try:
                node_type = node['type']
            except KeyError:
                # blank nodes have no type
                continue
            if node and node_type == type: 
                callback(game, player, node)


def remove_rubble(game, player):

    for_each_type(game, player, "rubble", remove_rubble_from_node)


def remove_rubble_from_node(game, player, node):

    # remove one rubble
    node['fields']['rubble_duration'] -= 1

    if node['fields']['rubble_duration'] <= 0: 
        # if all rubble is removed, clear from board
        set_node(game, player, node['row'], node['x'], {})


def heal(game, player):

    for_each_unit(game, player, heal_unit)


def heal_unit(game, player, unit):
    unit['damage'] = 0


def damage_unit(game, amount, target, source):

    if not target['damage']:
        target['damage'] = 0

    target['damage'] += amount

    if target['damage'] >= target['fields']['defense']:
        kill_unit(game, target)


def kill_unit(game, target):

    if target['fields']['rubble_duration'] > 0:
        # leave rubble
        target['type'] = 'rubble'

    else:
        # remove from game
        board = get_board(game, player)
        set_node(game, player, target['row'], target['x'], {})

# returns name of winner, or false if noone has won
def is_game_over(game):

    for player in game['players']:
        if player['life'] <= 0:
            return get_opponent_name(game, player)
        
    if game['goal'] == 'kill units':
        opp = get_opponent_name(game, game['player'])
        if each_unit(game, opp).length == 0:
            return game['player']
        
    return False

