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


# given the current hand and resources, returns
# an array with the shorthand move format
# of everything that can be done from here onward
def get_all_possible_turns(game, player):

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
        for card in game_master.get_player(game, player)['hand']:

            # copy 
            g = deepcopy(game)
            game_master.discard(g, player, card['pk'])
            game_master.tech(g, player, 1)
            game_master.get_player(g, player)['tech_ups_remaining_this_turn'] -= 1
            
            # record turn possibilities
            tech_turn = "%s tech %s" % (player, card['pk'])
            for poss in get_all_possible_turns(g, player):
                turns.append("%s\n%s" % (tech_turn, poss))

        # this is sort of a cludge. basically, it forces the AI to tech first
        # if they are going to tech, or to not do it at all. since teching later
        # in the turn is identical to teching at the beginning, it reduces the
        # number of redundant possibilities the AI is going to consider.
        g = deepcopy(game)
        game_master.get_player(g, player)['tech_ups_remaining_this_turn'] -= 1
        for poss in get_all_possible_turns(g, player):
            turns.append("%s\n%s" % (tech_turn, poss)) 

        teched_this_step = True

    if not teched_this_step:

        # try playing each card
        for card in game_master.get_player(game, player)['hand']:

            if game_master.get_player(game, player)['current_tech'] >= card['fields']['tech_level']:

                for node_str in get_valid_targets(game, player, card): 

                    # we can afford to play it and have a spot
                    g = deepcopy(game)

                    # node_str = "player row x" 
                    toks = node_str.split(" ")
                    game_master.play(g, player, card['pk'], toks[0], int(toks[1]), int(toks[2])) 

                    play_turn = "%s play %s %s" % (player, card['pk'], node_str)
                    # play each card in each valid position
                    for poss in get_all_possible_turns(g, player):
                        turns.append("%s\n%s" % (play_turn, poss))
                
    return turns 




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
    turns = get_all_possible_turns(game, player)

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
