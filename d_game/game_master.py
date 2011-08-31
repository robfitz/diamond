import random, logging, copy, simplejson

from django.core import serializers
from d_game import cached

from django.core.cache import cache


ANON_PLAYER_NAME = "guest"


def log_board(game, log_note):

    player = game['player']
    opp = get_opponent_name(game,game['player'])

    opp_str = ""

    for row in range(0, 3):
        line = ""
        for col in range(-2, row + 1):
            id = ''
            if col >= 0 or abs(col) <= row:
                node = get_node(game, opp, row, col)
                if node and node['type'] == 'unit':
                    id = "%s[%s]" % (node['fields']['name'][:3], node['damage'])
                elif node and node['type'] == 'rubble':
                    id = 'rubble'
                else:
                    id = '------'
            else:
                id = '      '
            line = "%s %s" % (line, id)
        opp_str = "%s \n%s" % ( opp_str, line )

    player_str = ""
    for row in range(0, 3):
        line = ""
        for col in range(-2, row + 1):
            id = ''
            if col >= 0 or abs(col) <= row:
                node = get_node(game, player, row, col)
                if node and node['type'] == 'unit':
                    id = "%s[%s]" % (node['fields']['name'][:3], node['damage'])
                elif node and node['type'] == 'rubble':
                    id = 'rubble'
                else:
                    id = '------'
            else:
                id = '      '
            line = "%s %s" % (line, id)
        player_str = "%s \n%s" % ( line, player_str )

    board_str = "%s \n\n%s\n" % (opp_str, player_str)

    from d_game.models import Match
    match = Match.objects.get(id=game['pk'])
    match.log = "".join([log_note, board_str, match.log])
    match.save()


def init_game(match):

    if match.player:
        player = match.player.username
    else:
        player = ANON_PLAYER_NAME

    game = {    
            'pk': match.pk,
            'type': match.type,
            'goal': match.goal,
            'current_phase': 0,
            'player': player,
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


def do_turns(game, player_moves):

    from d_game import ai

    logging.info("XX game master doing turn for player moves; %s" % player_moves)

    player_name = game['player']
    opponent_name = get_opponent_name(game, player_name)

    # turn init
    heal(game, player_name) 

    do_turn(game, player_name, player_moves)

    # AI turn init
    heal(game, opponent_name) 
    draw_up_to(game, opponent_name, 5) 

    # AI decides what to do (but doens't actually affect the 
    # game state yet
    ai_turn = ai.get_turn(game, opponent_name) 
    ai_moves = [ ai_turn[0]['shorthand'], ai_turn[1]['shorthand'] ]

    # log the turn for client-server verification purposes
    # and process its decisions.
    game_before_ai = simplejson.dumps(game) 
    do_turn(game, opponent_name, ai_moves) 
    game_after_ai = simplejson.dumps(game) 

    # get 2 new cards for player 
    # this is out of order because we're actually drawing
    # for the player's next turn, not the current one just processed
    draw_cards = draw_up_to(game, player_name, 5)

    # save turn changes on server
    cached.save(game)

    #serialize and ship it
    hand_and_turn_json = """{
            'player_draw': %s,
            'ai_turn': %s,
            'verify_board_state_before_ai': %s,
            'verify_board_state_after_ai': %s,
            }""" % (simplejson.dumps(draw_cards),
                    simplejson.dumps(ai_turn),
                    game_before_ai,
                    game_after_ai)

    return hand_and_turn_json


def do_turn(game, player, moves, is_ai=False):

    # check win condition
    if is_game_over(game):
        winner = is_game_over(game) 
        logging.info("********** game over, winner=%s" % is_game_over(game))
        return


    log_board(game, "%s, before first play" % player)

    # first play
    do_turn_move(game, player, moves[0])

    log_board(game, "%s, after first play" % player)

    # attack!
    do_attack_phase(game, player)

    log_board(game, "%s, after attack" % player)

    # check win condition
    if is_game_over(game):
        winner = is_game_over(game) 
        logging.info("********** game over, winner=%s" % is_game_over(game))
        return

    # second play
    do_turn_move(game, player, moves[1])

    log_board(game, "%s, after second play" % player)

    # cleanup
    remove_rubble(game, player)

    log_board(game, "%s, after rubble cleanup" % player)


def do_turn_move(game, player, move):

    toks = move.split(' ')

    try:
        action = toks[1]
    except:
        action = 'pass'

    if action == 'pass':
        pass

    elif action == "surrender":
        logging.info("TODO: %s surrender" % player)

    elif action == 'tech':
        card_id = toks[2]
        if discard(game, player, card_id):
            tech(game, player, 1)

    elif action == 'play':
        logging.info("WWW player %s playing card for move: %s" % (player, move))
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
        logging.info("WWW tried discarding: %s" % card)
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
            logging.info("YYY added unit to board for %s at %s_%s" % (player, node["row"], node["x"]))


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

    logging.info("XXX do attack phase by %s" % attacking_player)
    for_each_unit(game, attacking_player, do_attack)


def do_attack(game, attacking_player, unit):

    logging.info("XXX do attack by %s" % attacking_player)
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

            logging.info("XXX bumped into player %s with goal %s" % (attacked_player, game['goal']))

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
                logging.info("RRR got node of type (%s) %s for player %s" % (type, node, player))
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

    logging.info("UUU healed for %s" % player)

    for_each_unit(game, player, heal_unit)


def heal_unit(game, player, unit):
    unit['damage'] = 0


def damage_unit(game, amount, target, source):

    if not target['damage']:
        target['damage'] = 0

    target['damage'] += amount
    logging.info("ZZ damaged unit to: %s" % target['damage'])

    if target['damage'] >= target['fields']['defense']:
        logging.info("ZZ and it's dead")
        kill_unit(game, target)


def kill_unit(game, target):
    logging.info("ZZ killing unit")

    if target['fields']['rubble_duration'] > 0:
        # leave rubble
        target['type'] = 'rubble'
        logging.info("ZZ set type to rubble")

    else:
        # remove from game
        board = get_board(game, player)
        set_node(game, player, target['row'], target['x'], {})

# returns name of winner, or false if noone has won
def is_game_over(game):

    for player in game['players']:
        if game['players'][player]['life'] <= 0:
            logging.info("*** game is over from loss of life: %s" % player)
            return player
        
    if game['goal'] == 'kill units':
        opp = get_opponent_name(game, game['player'])
        if len(each_unit(game, opp)) == 0:
            logging.info("*** game is over from puzzle condition kill units: %s" % player)
            return game['player']
        else:
            logging.info("*** goal is to kill units, but not empty because:%s has %s" % (opp, len(each_unit(game, opp))))
        
    return False

