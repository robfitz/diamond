import random, logging, copy, simplejson

from django.core import serializers
from d_game import cached

from django.core.cache import cache


ANON_PLAYER_NAME = "guest"


def log_board(game, log_note):

    player = game['player']
    opp = get_opponent_name(game, game['player'])

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
                    'current_tech': match.friendly_tech,
                    'tech_ups_remaining_this_turn': 1,
                    'hand': [],
                    'num_to_draw': 1,
                    'library': cached.get_cards(match.friendly_deck_cards),
                    'board': { },
                },
                'ai': {
                    'life': match.ai_life,
                    'tech': match.ai_tech,
                    'current_tech': match.ai_tech,
                    'tech_ups_remaining_this_turn': 1,
                    'hand': [],
                    'num_to_draw': 1,
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

    draw_up_to(game, 'ai', 5)

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

    player_name = game['player']
    opponent_name = get_opponent_name(game, player_name)

    logging.info("XXX player hand: %s" % get_player(game, player_name)['hand'])

    # turn init
    heal(game, player_name) 
    refill_tech(game, player_name)
    remove_summoning_sickness(game, player_name)

    do_turn(game, player_name, player_moves)

    # AI turn init
    heal(game, opponent_name) 
    refill_tech(game, opponent_name)
    draw(game, opponent_name, get_player(game, opponent_name)['num_to_draw'])
    remove_summoning_sickness(game, opponent_name)

    # AI decides what to do (but doens't actually affect the 
    # game state yet
    ai_moves, ai_turn = ai.get_turn(game, opponent_name) 

    # log the turn for client-server verification purposes
    # and process its decisions.
    game_before_ai = simplejson.dumps(game) 
    do_turn(game, opponent_name, ai_moves) 
    game_after_ai = simplejson.dumps(game) 

    # get 2 new cards for player 
    # this is out of order because we're actually drawing
    # for the player's next turn, not the current one just processed
    logging.info("XXX player is about to draw %s" % get_player(game, player_name)['num_to_draw'])

    draw_cards = draw(game, player_name, get_player(game, player_name)['num_to_draw'])

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
    winner = is_game_over(game) 
    if winner:
        logging.info("********** game over, winner=%s" % winner)
        return 

    i = 1
    for move in moves:
        do_turn_move(game, player, move)
        log_board(game, "%s, after play #%s" % (player, i))
        i += 1 

    # check win condition
    winner = is_game_over(game) 
    if winner:
        logging.info("********** game over, winner=%s" % is_game_over(game))
        return

    log_board(game, "%s, before attack" % player)

    # attack!
    do_attack_phase(game, player)

    log_board(game, "%s, after attack" % player) 
   
    # cleanup
    remove_rubble(game, player)

    log_board(game, "%s, after rubble cleanup" % player)


def do_turn_move(game, player, move):

    toks = move.split(' ')

    if player == "robfitz":
        logging.info("YYY turn move: %s %s" % (player, move))

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
            get_player(game, player)['tech_ups_remaining_this_turn'] -= 1

    elif action == 'play':
        card_id = toks[2]
        node_owner = toks[3]
        row = toks[4]
        x = toks[5]

        play(game, player, card_id, node_owner, row, x) 


def refill_tech(game, player):
    get_player(game, player)['current_tech'] = get_player(game, player)['tech'];
    get_player(game, player)['tech_ups_remaining_this_turn'] = 1
        

# return False if was an illegal play
def play(game, player, card_id, node_owner, row, x, ignore_constraints=False):

    if not ignore_constraints:
        # remove card from hand
        card = discard(game, player, card_id) 
        if not card:
            if player == 'robfitz': logging.info("XXX failed to discard")
            # fail if requested card was not in hand
            return False 

        if get_player(game, player)['current_tech'] >= card['fields']['tech_level']:
            # remove casting cost from available tech resources
            get_player(game, player)['current_tech'] -= card['fields']['tech_level']
        else:
            if player == 'robfitz': logging.info("XXX not enough resources")
            # didn't have enough resources to cast it
            return False

    else:
        from d_cards.models import Card
        card = Card.objects.get(id=card_id)

        from django.forms.models import model_to_dict
        card = { 'pk': card.pk,
                'fields': model_to_dict(card, fields=[], exclude=[]) 
            }

    if player == "robfitz": logging.info("XXX robfitz playing")
    
    if player == "robfitz":
        logging.info("XXX playing card: %s" % card['pk'])
        logging.info("dir: %s" % dir(card['fields']))

    # process 'on-cast' effects
    if card['fields']['tech_change']:
        tech(game, player, card['fields']['tech_change'])
    if card['fields']['resource_bonus']:
        get_player(game, player)['current_tech'] += card['fields']['resource_bonus']

    if card['fields']['draw_num']:
        logging.info("XXX card fields draw num")
        # bonus cards are added to player's next draw phase
        get_player(game, player)['num_to_draw'] += card['fields']['draw_num']
        logging.info("XXX card cast increased player num to draw by %s to %s" % (card['fields']['draw_num'], get_player(game, player)['num_to_draw']))


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

        if card['fields']['direct_damage']:
            # direct damage 
            target = get_board(game, node_owner)["%s_%s" % (node["row"], node['x'])]
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
            card['attack_delay'] = 1

            # deep copy in case of multiple targets for same card
            get_board(game, player)["%s_%s" % (node["row"], node["x"])] = copy.deepcopy(card)


def discard(game, player, card_id):
    if player=='robfitz':
        logging.info("XXX Hand: %s" % get_player(game, player)['hand'])
        logging.info("XXX trying to discard: %s" % card_id)

    i = 0
    for card in get_player(game, player)['hand']:
        if int(card['pk']) == int(card_id):
            if player=='robfitz':
                logging.info("XXX found card to discard")
            card = get_player(game, player)['hand'][i]
            del get_player(game, player)['hand'][i]
            if player=='robfitz':
                logging.info("XXX discarded")
            return card
        i += 1
    return False


def tech(game, player, amount):
    p = get_player(game, player)
    p['tech'] += amount 

    if amount < 0 and p['current_tech'] > p['tech']:
        # if we teched down via a card downside, and if and if our maximum tech
        # is lower than our available tech, lop off a couple available tech so we
        # don't have more than our max allocation. 
        # This situation will rarely arise, however, since in casting something
        # with a negative tech drawback, you'll have already used some of your 
        # available tech.
        p['current_tech'] = p['tech'] 


def draw_up_to(game, player, total):

    num = total - len(get_player(game, player)['hand'])
    return draw(game, player, num)


def draw(game, player, num):

    # remove from deck
    drawn = get_player(game, player)['library'][:num]
    del get_player(game, player)['library'][:num]

    # add to hand
    get_player(game, player)['hand'].extend(drawn)

    # reset draw bonus to normal levels
    get_player(game, player)['num_to_draw'] = 1

    # return the delta
    return drawn


def do_attack_phase(game, attacking_player):

    for_each_unit(game, attacking_player, do_attack)


def do_attack(game, attacking_player, unit):


    if unit['attack_delay'] > 0:
        # summoning sickness
        return

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

def remove_summoning_sickness(game, player):

    for_each_unit(game, player, remove_unit_summoning_sickness)

def remove_unit_summoning_sickness(game, player, unit):
    if unit['attack_delay'] > 0:
        unit['attack_delay'] -= 1


def damage_unit(game, amount, target, source):

    try:
        target['damage'] += amount
    except KeyError:
        target['damage'] = amount 

    if target['fields']['attack_type'] == 'counterattack':
        if source['fields']['attack_type'] != 'flying': 
            # retaliation from counterattackers to non-flying attackers
            damage_unit(game, target['fields']['attack'], source, target)

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
        if game['players'][player]['life'] <= 0:
            logging.info("*** game is over from loss of life: %s" % get_opponent_name(game, player))
            return get_opponent_name(game, player)
        
    if game['goal'] == 'kill units':
        opp = get_opponent_name(game, game['player'])
        if len(each_unit(game, opp)) == 0:
            logging.info("*** game is over from puzzle condition kill units: %s" % player)
            return game['player']
        else:
            logging.info("*** goal is to kill units, but not empty because:%s has %s" % (opp, len(each_unit(game, opp))))
        
    return False

