# turn format:
#
# player play card_id node_owner row x
# player tech card_id
# player pass
# 
# robfitz play 123 ai 2 -1
# robfitz tech 123
# robfitz pass 

import logging
from datetime import datetime, timedelta

from utils.util import deepish_copy as deepcopy
from utils.util import one_level_deepcopy
from d_game import game_master, cached 

example = { 
        'player': 'ai',
        'action': 'play/tech/pass',
        'card': { 
            'card_obj': 'card_obj' 
        },
        'target': {
            'player': 'robfitz',
            'row': 2,
            'x': 1
        }
    }

def get_all_possible_turns(game, player, time_log):

    turns = ["%s pass" % player]
    boards = get_simple_board(game, player)
    current_resources = game_master.get_player(game, player)['current_tech']
    hand = game_master.get_player(game, player)['hand']

    simple_board = one_level_deepcopy(boards)

    # sort cards so that anything with a positive immediate bonus
    # is at the beginning of the list. this allows us to go strictly
    # linearly instead of trying all paths
    cards_insta_bonus = []
    cards_regular = []
    for card in hand:
        if card['fields']['resource_bonus']:
            cards_insta_bonus.append(card)
        else:
            cards_regular.append(card)

    cards_insta_bonus = sorted(cards_insta_bonus, key=lambda card: card['fields']['tech_level'])
    cards_regular = sorted(cards_regular, key=lambda card: card['fields']['tech_level'])

    # bonus cards first, then others, sorted by cost in both cases (sorted so you can chain multiple
    # resource-granting abilities to get to a higher total level)
    hand = cards_insta_bonus
    hand.extend(cards_regular) 

    str = ""
    for card in hand:
        str = " ".join([str, card['fields']['name']]) 
    logging.info("**** AI hand for get all poss turns: %s" % str)

    # get possibilities if we don't tech at all
    simple_hand = hand[:]
    for poss in get_moves(simple_hand, simple_board, current_resources):
        turns.append("%s" % poss)

    # get possibilities if we begin the turn by teching
    i = 0
    teched_with_pks = []
    for card in hand:

        if card['pk'] in teched_with_pks:
            logging.info("***** already teched with %s" % card['pk'])
            # fruitless to create paths for teching w/ identical cards
            continue

        teched_with_pks.append( card['pk'] )

        # hand without the discarded card
        without = hand[:i]
        without.extend( hand[i+1:] ) 

        tech_turn = "%s tech %s" % (player, card['pk'])
        turns.append(tech_turn)

        simple_hand = without
        simple_board = one_level_deepcopy(boards)
        
        for poss in get_moves(simple_hand, simple_board, current_resources):
            turns.append("%s\n%s" % (tech_turn, poss))

        i += 1
    
    return turns

def get_moves_2(hand, boards, resources):
    ''' sort all cards, by whether it has an up-front effect
    (like adding resources) and then either play or don't play
    each card until out of resources '''

    pass

# assumes teching is already done. given what's remaining,
# returns an array of shorthand moves showing what's possible
def get_moves(hand, boards, resources):

    turns = []
    card_i = 0

    played_card_pks = []

    for card in hand:

        if card['pk'] in played_card_pks:
            # fruitless to create paths for playing identical cards at same point
            logging.info("____ already played card %s" % card['pk'])
            card_i += 1
            continue

        played_card_pks.append( card['pk'] )

        if resources >= card['fields']['tech_level']:
            # we can afford to play it -- give it a shot

            targets = get_simple_valid_targets(boards, boards['friendly_name'], card)

            for node_str in targets:

                # make some copies pointing at new data
                boards_copy = one_level_deepcopy(boards)

                toks = node_str.split(" ")
                simple_board_play(boards_copy, boards['friendly_name'], card, toks[0], int(toks[1]), int(toks[2]))

                resources_copy = resources - card['fields']['tech_level']
                resources_copy += card['fields']['resource_bonus']

                play_turn = "%s play %s %s" % (boards['friendly_name'], card['pk'], node_str)
                turns.append(play_turn)

                # try playing the rest of the hand cards
                hand_copy = hand[card_i + 1 : ] 
                for poss in get_moves(hand_copy, boards_copy, resources_copy):
                    turns.append("%s\n%s" % (play_turn, poss))

        # try playing the rest of the hand cards after NOT PLAYING this one.
        # note that this is only necessary if we're throwing away the earlier index hand
        # cards on the assumption they are sorted.
        hand_copy = hand[card_i + 1 : ]
        boards_copy = one_level_deepcopy(boards)
        for poss in get_moves(hand_copy, boards_copy, resources):
            turns.append(poss) 
    
        card_i += 1

    return turns





def get_simple_board(game, player):
    ''' Produces something out such that: boards[friendly_name/enemy_name]['r_x'] = 'unit/rubble/empty'.
        This board is in relation to a single player wrt friendly_name/enemy_name '''

    enemy = game_master.get_opponent_name(game, player)

    friendly_board = {}
    enemy_board = {}
    
    for row in range(0, 3):
        for col in range(-row, row + 1):
            
            friendly_board['%s_%s' % (row, col)] = get_simple_node(game, player, row, col)
            enemy_board['%s_%s' % (row, col)] = get_simple_node(game, enemy, row, col)

    return { 
            'friendly_name': player,
            'enemy_name': enemy,
            player: friendly_board,
            enemy: enemy_board 
            }


def get_simple_node(game, player, row, col):

    node = game_master.get_node(game, player, row, col)

    try:
        node_type = node['type']
        return node_type
    except KeyError:
        return 'empty' 


# given the current hand and resources, returns
# an array with the shorthand move format
# of everything that can be done from here onward
def __dep__get_all_possible_turns(game, player, time_log):

    time_begin = datetime.now()

    turns = ["%s pass" % player]
    best_turn = (heuristic(game, player), turns[0])

    if len(game_master.get_player(game, player)['hand']) == 0:
        # no cards left? we're done!
        return turns

    teched_this_step = False

    # try teching each card
    if game_master.get_player(game, player)['tech_ups_remaining_this_turn'] > 0:
        # we're still allowed to tech up, so every card in
        # our hand is fair game for that

        teched_with_ids = []

        for card in game_master.get_player(game, player)['hand']:

            if card['pk'] in teched_with_ids:
                # it's redundant to tech w/ multiple copies of the same card
                continue

            # copy 
            g = deepcopy(game)
            game_master.discard(g, player, card['pk'])
            game_master.tech(g, player, 1)
            game_master.get_player(g, player)['tech_ups_remaining_this_turn'] -= 1

            teched_with_ids.append(card['pk'])
            
            # record turn possibilities
            tech_turn = "%s tech %s" % (player, card['pk'])
            for poss in get_all_possible_turns(g, player, time_log):
                turns.append("%s\n%s" % (tech_turn, poss))

        # this is sort of a cludge. basically, it forces the AI to tech first
        # if they are going to tech, or to not do it at all. since teching later
        # in the turn is identical to teching at the beginning, it reduces the
        # number of redundant possibilities the AI is going to consider.
        g = deepcopy(game)
        game_master.get_player(g, player)['tech_ups_remaining_this_turn'] -= 1
        for poss in get_all_possible_turns(g, player, time_log):
            turns.append("%s\n%s" % (tech_turn, poss)) 

        teched_this_step = True

    if not teched_this_step:

        # try playing each card
        for card in game_master.get_player(game, player)['hand']:

            if game_master.get_player(game, player)['current_tech'] >= card['fields']['tech_level']:

                temp = datetime.now()
                targets = get_valid_targets(game, player, card)
                time_log['get_valid_targets'] += datetime.now() - temp

                for node_str in targets:

                    # we can afford to play it and have a spot
                    temp = datetime.now()
                    g = deepcopy(game)
                    time_log['deepcopy'] += datetime.now() - temp

                    # node_str = "player row x" 
                    temp = datetime.now()
                    toks = node_str.split(" ")
                    game_master.play(g, player, card['pk'], toks[0], int(toks[1]), int(toks[2])) 
                    time_log['play'] += datetime.now() - temp

                    play_turn = "%s play %s %s" % (player, card['pk'], node_str)
                    # play each card in each valid position
                    for poss in get_all_possible_turns(g, player, time_log):
                        turns.append("%s\n%s" % (play_turn, poss))
                

    return turns 


def simple_board_play(boards, player, card, node_owner, row, x):

    ''' currently we only update the board to show critters being
    summoned. this allows for some invalid play states (like
    using direct damage to kill a unit and then thinking he's
    still on the board. Those are weeded out during the actual
    play/heuristic simulations. '''

    if not card['fields']['defense']:
        return 

    nodes = []
    if card['fields']['target_aiming'] == 'chosen': 
        boards[node_owner]['%s_%s' % (row, x)] = 'unit'

    elif card['fields']['target_aiming'] == 'all': 
        for row in range(3):
            for col in range(-row, row+1): 
                if boards[node_owner]["%s_%s" % (row, col)] == "empty":
                    boards[node_owner]['%s_%s' % (row, x)] = 'unit'
                    

# uses a simple board format where boards['friendly/enemy']['r_x'] == 'unit/empty/rubble'
def get_simple_valid_targets(boards, player, card):

    nodes = []
    enemy = boards['enemy_name']

    if card['fields']['target_alignment'] == 'any': 
        target_players = [player, enemy]
    elif card['fields']['target_alignment'] == 'friendly':
        target_players = [ player ]
    elif card['fields']['target_alignment'] == 'enemy':
        target_players = [ enemy ]

    for target_player in target_players:

        board = boards[target_player]

        for row in range(3):
            for x in range(-row, row+1): 

                node = board["%s_%s" % (row, x)]

                if card['fields']['target_occupant'] == node: 
                    nodes.append("%s %s %s" % (target_player, row, x))

    return nodes 




# in shorthand node format:
# ["player row x", "player row x"]
def get_valid_targets(game, player, card):

    nodes = []
    target_players = []

    if card['fields']['target_alignment'] == 'friendly' or card['fields']['target_alignment'] == 'any': 
        target_players.append(player)
    if card['fields']['target_alignment'] == 'enemy' or card['fields']['target_alignment'] == 'any': 
        target_players.append(game_master.get_opponent_name(game, player))

    for target_player in target_players:

        board = game_master.get_board(game, target_player) 

        for row in range(3):
            for x in range(-row, row+1): 

                if card['fields']['target_occupant'] == 'unit': 
                    node = board["%s_%s" % (row, x)]
                    node_type = None
                    try:
                        if node['type'] == 'unit':
                            nodes.append("%s %s %s" % (target_player, row, x))
                    except KeyError:
                        # blank nodes have no type
                        continue

                elif card['fields']['target_occupant'] == 'empty': 
                    node = board["%s_%s" % (row, x)]
                    is_empty = False
                    if not node:
                        is_empty = True
                    else:
                        try:
                            if node['type'] == 'empty':
                                is_empty = True
                        except KeyError:
                            # blank nodes have no type
                            is_empty = True
                    if is_empty:
                        nodes.append("%s %s %s" % (target_player, row, x)) 

    return nodes 


def get_turn(game, player):

    time_begin = datetime.now()

    # get list of all possible first moves, including teching & passing

    best = (-100000, "")

    time_log_obj = {'get_valid_targets': timedelta(), 'deepcopy': timedelta(), 'play': timedelta()}
    turns = get_all_possible_turns(game, player, time_log_obj)

    time_log = """get_all_possible_turns(): %s  
  get valid targets:  %s
  deepcopy game:   %s 
  simulate play: %s\n
""" % (len(turns),
        time_log_obj['get_valid_targets'],
        time_log_obj['deepcopy'],
        time_log_obj['play'])

    logging.info("**** ai deciding what to do, got __%s__ turns" % len(turns))
    logging.info(turns)

    from d_game.models import Match
    match = Match.objects.get(id=game['pk'])
    match.log = "".join([time_log, match.log])
    match.save()

    time_got_turns = datetime.now()

    time_in_human_attacks = timedelta()
    time_in_ai_attacks = timedelta()
    time_heuristic = timedelta()

    time_deepcopy = timedelta()
    time_do_turn_move = timedelta()

    opponent = game_master.get_opponent_name(game, player)

    for turn in turns:
        temp_timer = datetime.now()
        g_copy = deepcopy(game)
        time_deepcopy += datetime.now() - temp_timer

        temp_timer = datetime.now()
        for move in turn.split('\n'):
            game_master.do_turn_move(g_copy, player, move)
        time_do_turn_move += datetime.now() - temp_timer

        # do AI attack
        temp_timer = datetime.now()
        game_master.do_attack_phase(g_copy, player)
        time_in_ai_attacks += datetime.now() - temp_timer

        # remove [human] player summoning sickness and simulate attack
        # to make the AI a bit more defensive
        temp_timer = datetime.now()
        game_master.heal(g_copy, opponent)
        game_master.remove_summoning_sickness(game, opponent) 
        game_master.do_attack_phase(g_copy, opponent) 
        time_in_human_attacks += datetime.now() - temp_timer

        temp_timer = datetime.now()
        h = heuristic(g_copy, player) 
        if h > best[0]:
            best = (h, turn) 
        time_heuristic += datetime.now() - temp_timer

    # convert best pair into play array 
    best_moves = best[1].split('\n') 
    turn = []
    for move in best_moves:
        toks = move.split(' ')
        play = { 
                'shorthand': move,
                'player': player,
                'action': toks[1]
                }

        if len(toks) > 2:
            play['card'] = cached.get_card(toks[2])

        if len(toks) > 5:
            play['node'] = {
                    'player': toks[3],
                    'row': toks[4],
                    'x': toks[5]
                }

        turn.append(play)


    time_log = """Total ai.get_turn:    %s
  Getting all turns:  %s (%s possibilities)
  Doing turn moves:   %s 
  Simulating attacks: %s
  Finding heuristic:  %s
  Deepcopying game:   %s\n
""" % (datetime.now() - time_begin,
        time_got_turns - time_begin, len(turns),
        time_do_turn_move,
        time_in_human_attacks + time_in_ai_attacks,
        time_heuristic,
        time_deepcopy)

    from d_game.models import Match
    match = Match.objects.get(id=game['pk'])
    match.log = "".join([time_log, match.log])
    match.save()

    logging.info("^^^^^ got best AI play: %s" % best_moves)
                
    return (best_moves, turn)


def heuristic(game, player):

        h = 0

        opponent = game_master.get_opponent_name(game, player)

        for unit in game_master.each_unit(game, player):
            h += unit['fields']['unit_power_level']

        for unit in game_master.each_unit(game, opponent):
            h -= 1.1 * unit['fields']['unit_power_level']

        h += 0.4 * game['players'][player]['life']
        h -= 0.4 * game['players'][opponent]['life']

        for card in game['players'][player]['hand']:
            card_tech = card['fields']['tech_level']
            player_tech = game['players'][player]['tech']

            # cards you can cast are worth a bit of potential
            if card_tech <= player_tech:
                h += 0.2 * card_tech

            # cards you can almost cast are worth a little less
            elif card_tech == 1 + player_tech:
                h += 0.1 * card_tech

        for rubble in game_master.each_type(game, player, 'rubble'):
            h -= 0.33

        for rubble in game_master.each_type(game, opponent, 'rubble'):
            h += 0.33 

        if game['players'][player]['life'] <= 0:
            return h - 1000
        elif game['players'][opponent]['life'] <= 0:
            return h + 1000
        else: 
            return h
