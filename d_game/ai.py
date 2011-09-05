# turn format:
#
# player play card_id node_owner row x
# player tech card_id
# player pass
# 
# robfitz play 123 ai 2 -1
# robfitz tech 123
# robfitz pass 


import logging, copy

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


# in shorthand move format:
# ["player action [card [node_owner row x]]"]
def get_all_possible_moves(game, player):

    moves = [] 

    # do nothing
    moves.append("%s pass" % player)

    for card in game_master.get_player(game, player)['hand']: 
        # use each card to tech up
        moves.append("%s tech %s" % (player, card['pk']))

        if card['fields']['tech_level'] <= game['players'][player]['current_tech']:
            # only consider casting it if we have enough tech

            for node_str in get_valid_targets(game, player, card): 
                # play each card in each valid position
                moves.append("%s play %s %s" % (player, card['pk'], node_str))

    return moves 


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

    # get list of all possible first moves, including teching & passing

    moves = get_all_possible_moves(game, player)
    logging.info("####### all possible moves")
    logging.info(moves)
    logging.info("#######")

    game_original = game
    opponent = game_master.get_opponent_name(game, player)

    best_h = -10000
    best_moves = None

    # for each first move
    for move in moves:

        # load clean game state
        game = copy.deepcopy(game_original)

        # do first move
        game_master.do_turn_move(game, player, move)

        # simulate attack
        game_master.do_attack_phase(game, player)
        
        # get list of all possible 2nd moves 
        second_moves = get_all_possible_moves(game, player)

        # for each 2nd move
        for second_move in second_moves:

            second_game = copy.deepcopy(game)

            # do second move
            game_master.do_turn_move(second_game, player, second_move)

            # simulate attack and counterattack to make it a little brighter
            game_master.heal(game, opponent)
            game_master.do_attack_phase(game, opponent)
            game_master.heal(game, player)
            game_master.do_attack_phase(game, player) 

            # get board heuristic value
            h = heuristic(second_game, player)

            # save best move pairing
            if not best_moves or h > best_h:
                best_moves = [move, second_move]
                best_h = h

    # convert best pair into play array 
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

    logging.info("^^^^^ got best AI play: %s" % best_moves)
                
    return turn


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
