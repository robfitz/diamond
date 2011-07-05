import logging, random

from django.db import models
from django.contrib import admin
import simplejson

from d_cards.models import Card, ShuffledLibrary, Deck
from d_board.models import Node



class Match(models.Model):
    """ A battle between 2 players (or a player and AI) """

    MATCH_TYPES = (
            ("puzzle", "Puzzle"), 
            ("ai", "P vs AI"),
            ("pvp", "P vs P"),
        )

    type = models.CharField(max_length=10, choices=MATCH_TYPES)

    winner = models.CharField(max_length=20, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    friendly_library = models.OneToOneField(ShuffledLibrary)
    ai_library = models.OneToOneField(ShuffledLibrary, null=True)

    friendly_life = models.IntegerField(default=10)
    ai_life = models.IntegerField(default=10)

    friendly_tech = models.IntegerField(default=1)
    ai_tech = models.IntegerField(default=1)



class Puzzle(models.Model):

    name = models.CharField(max_length=50, default="", blank=True)

    order = models.DecimalField(max_digits=6, decimal_places=3)

    # starting positions defined by PuzzleStartingUnit set

    # starting life
    player_life = models.IntegerField(default=1)

    # goal: destroy all units

    player_deck = models.ForeignKey(Deck, blank=True, null=True)


    def get_setup_turn(self):

        starting_units = PuzzleStartingUnit.objects.filter(puzzle=self)

        turn = Turn()

        if len(starting_units) > 0:
            u = starting_units[0]
            turn.play_1 = u.unit_card
            turn.target_alignment_1 = "ai"
            turn.target_node_1 = u.location

            if len(starting_units) > 1:
                u = starting_units[1]
                turn.play_2 = u.unit_card
                turn.target_alignment_2 = "ai"
                turn.target_node_2 = u.location 

        return turn


    def __unicode__(self):

        return "%d: %s" % (self.order, self.name)


class PuzzleStartingUnit(models.Model):

    OWNER_CHOICES = (
            ("player", "Player"), 
            ("ai", "AI"),
        )

    puzzle = models.ForeignKey(Puzzle)

    owner = models.CharField(max_length=10, default="ai")

    unit_card = models.ForeignKey(Card)
    location = models.ForeignKey(Node) 

    # TODO: not implemented
    must_be_killed_for_victory = models.BooleanField(default=True)


    def __unicode__(self):

        return "%s for %s" % (self.unit_card, self.puzzle)


class Unit(models.Model):
    """ A Unit is created when a card is played on the board,
        and is specific to a single match. """

    # card i represent
    card = models.ForeignKey(Card) 

    # game i'm a part of
    match = models.ForeignKey(Match)

    # "friendly" or "ai"
    owner_alignment = models.CharField(max_length=10)

    # location on the board
    row = models.IntegerField()
    x = models.IntegerField()

    # how much damage i've suffered
    damage = models.IntegerField(default=0)


    def heal(self):
        self.damage = 0


    # returns true if the damage was fatal
    def suffer_damage(self, amount, save_to_db):
        self.damage += amount

        if self.damage >= self.card.defense: 
            if save_to_db:
                self.die()

            return True
        else:
            if save_to_db:
                self.save()

        return False


    def die(self):
        self.delete()



class AI():
    """ AI player logic who decides what to play and do """
    

    def get_play(self, match, is_before_attack): 

        if not match.ai_library:
            # AI has no library in puzzle mode
            # when the initial board state is
            # all that matters for them
            return None

        hand_cards = match.ai_library.hand_cards()

        best_card = None
        best_target = None
        best_hval = -1000

        test_militia = Card(attack=1,
                defense=1,
                attack_type="melee",
                target_alignment="friendly",
                target_occupant="empty",
                target_aiming="all") 

        test_board = Board()
        for card in hand_cards: 
            remaining_hand_cards = list(hand_cards)
            remaining_hand_cards.remove(card)

            if card.tech_level > match.ai_tech:
                continue

            valid_targets = test_board.get_valid_targets_for(card, "ai")
            for target in valid_targets:
                test_board.load_from_match_id(match.id)
                test_board.cast("ai", card, target, False) 

                if is_before_attack:
                    # promote offensive play by simulating
                    # our AI attack
                    test_board.do_attack_phase("ai", False)
                else:
                    # promote more defensive play by
                    # simulating the player's attack.
                    # 
                    # TODO: make this even more conservative
                    #       by adding a 1/1 to each blank node
                    test_board.cast("friendly", test_militia, None, False)
                    test_board.do_attack_phase("friendly", False) 

                hval = test_board.get_ai_heuristic_value(hand_cards)

                if hval > best_hval:
                    best_hval = hval
                    best_card = card
                    best_target = target

            # test teching
            test_board.load_from_match_id(match.id)
            match.ai_tech += 1

            hval = test_board.get_ai_heuristic_value(hand_cards) 
            if hval > best_hval:
                best_hval = hval
                best_card = card
                best_target = "tech"

            match.ai_tech -= 1

        return { 'play': best_card,
                'target': best_target }


    def do_turn(self, board):

        match = board.match

        is_tech_1 = False
        is_tech_2 = False
        target_node_1 = None
        target_node_2 = None
        play_1 = None
        play_2 = None

        # ai draw
        if match.ai_library:
            match.ai_library.draw(2)

        first = self.get_play(match, True)
        if first:
            play_1 = first["play"]
            target_node_1 = first["target"] 
            match.ai_library.play(play_1.id)

        logging.info("** chose first cards to play") 

        #heal and attack
        board.heal("ai")

        if not target_node_1 or target_node_1 == "tech":
            is_tech_1 = True
            target_node_1 = None

            match.ai_tech += 1
            match.save()
        else:
            board.cast("ai", play_1, target_node_1, True)

        logging.info("BOARD AFTER AI CAST 1")
        board.log()

        board.do_attack_phase("ai", True)

        logging.info("BOARD AFTER AI ATTACK")
        board.log()

        second = self.get_play(match, False)
        if second:
            play_2 = second["play"]
            target_node_2 = second["target"]
            match.ai_library.play(play_2.id)

        # ai play second card 
        if not target_node_2 or target_node_2 == "tech": 
            logging.info("** ai 2nd cast: teching")
            is_tech_2 = True
            target_node_2 = None

            match.ai_tech += 1
            match.save()
        else:
            board.cast("ai", play_2, target_node_2, True)

        logging.info("BOARD AFTER AI CAST 2")
        board.log()

        ai_turn = Turn(play_1=play_1,
                target_node_1=target_node_1,
                is_tech_1=is_tech_1,
                target_alignment_1="friendly",
                play_2=play_2,
                target_node_2=target_node_2,
                is_tech_2=is_tech_2,
                target_alignment_2="friendly")

        return ai_turn 


class Board():
    """ A helper data structure which converts the database objects like
        Unit and Match into a handy data structure which knows how to perform
        game logic and then save itself back into the DB and session """

    nodes = { 'friendly': { }, 'ai': { } } 
    match = None

    node_power_levels = { "0_0": 2,
                "1_-1": 2, "1_0": 3, "1_1": 2,
                "2_-2": 1, "2_-1": 1, "2_0": 2, "2_1": 1, "2_2": 1 }


    def to_simple_json(self):

        simple_board = { 'friendly': { }, 'ai': { } } 
        simple_match = { 
                'tech': {
                    'friendly': self.match.friendly_tech,
                    'ai': self.match.ai_tech
                },
                'life': {
                    'friendly': self.match.friendly_life,
                    'ai': self.match.ai_life
                },
                'boards': simple_board
            }; 

        for align in simple_board:
            for key in self.nodes[align]:
                node = self.nodes[align][key]

                if not node:
                    continue
                elif node["type"] == "unit":
                    simple_board[align][key] = {
                            'type': "unit",
                            'card': node["unit"].card.pk,
                            'damage': node["unit"].damage
                        }
                elif node["type"] == "rubble":
                    simple_board[align][key] = {
                            'type': "rubble",
                            'amount': node.amount
                        } 

        return simplejson.dumps(simple_match) 


    def get_valid_targets_for(self, card, owner_alignment):

        valid_targets = []

        for row in range(3):
            for x in range(-row, row+1): 

                # gain points for having units
                node = self.nodes[owner_alignment]["%s_%s" % (row, x)]
                if not node:
                    valid_targets.append(Node.objects.get(row=row, x=x))

        return valid_targets

    def get_node_power(self, row, x):
        if row == 0 and x == 0:
            return 2
    
    def get_ai_heuristic_value(self, hand_cards): 

        #if self.match.friendly_life <= 0:
            #return 1000
        #elif self.match.ai_life <= 0:
            #return -1000
        
        hval = 0

        my_units = 0
        their_units = 0

        # units
        for row in range(3):
            for x in range(-row, row+1): 

                # gain points for having units
                node = self.nodes['ai']["%s_%s" % (row, x)]

                if node and node["type"] == 'unit': 
                    hval += node["unit"].card.unit_power_level 
                    my_units += node["unit"].card.unit_power_level

                # lose slightly more points for enemy units
                node = self.nodes['friendly']["%s_%s" % (row, x)]
                if node and node["type"] == 'unit': 
                    hval -= node["unit"].card.unit_power_level * 1.1 
                    their_units -= node["unit"].card.unit_power_level * 1.1 

        # life
        their_life = - self.match.friendly_life * 0.4
        my_life = self.match.ai_life * 0.4

        hval += their_life
        hval += my_life

        my_hand = 0
        # hand choices
        for card in hand_cards:

            # cards you can cast are worth lots
            if card.tech_level <= self.match.ai_tech:
                hval += 0.2 * card.tech_level
                my_hand+= 0.2 * card.tech_level

            # cards you can almost cast are worth a little
            elif card.tech_level == self.match.ai_tech + 1:
                hval += 0.1 * card.tech_level
                my_hand += 0.1 * card.tech_level

        my_board = 0
        their_board = 0

        # board choices
        for row in range(3):
            for x in range(-row, row+1): 

                # lose points for having rubble
                node = self.nodes['ai']["%s_%s" % (row, x)]
                if node and node["type"] == 'rubble':
                    hval -= node["rubble"] * self.node_power_levels["%s_%s" % (row, x)] * 0.33
                    their_board -= node["rubble"] * self.node_power_levels["%s_%s" % (row, x)] * 0.33

                # gain points for enemy rubble
                node = self.nodes['friendly']["%s_%s" % (row, x)]
                if node and node["type"] == 'rubble':
                    hval += node["rubble"] * self.node_power_levels["%s_%s" % (row, x)] * 0.33
                    my_board += node["rubble"] * self.node_power_levels["%s_%s" % (row, x)] * 0.33

        #logging.info("@@ got heuristic: %s from life=%s/%s, hand=%s, units=%s/%s, board=%s/%s" % (hval, my_life, their_life, my_hand, my_units, their_units, my_board, their_board))
        return hval


    def cast(self, owner_alignment, card_to_play, node_to_target, save_to_db):

        nodes = []
        if card_to_play.target_aiming == 'chosen': 
            nodes.append({ 'row': node_to_target.row, 'x': node_to_target.x})

        elif card_to_play.target_aiming == 'all':

            for row in range(3):
                for x in range(-row, row+1): 

                    if not self.nodes[owner_alignment]["%s_%s" % (row, x)]: 
                        nodes.append({ 'row': row, 'x': x });


        for node in nodes:

            if card_to_play.tech_change:
                # tech up SUUUUUN!
                if owner_alignment == "ai": 
                    self.match.ai_tech += card_to_play.tech_change
                else:
                    self.match.friendly_tech += card_to_play.tech_change

            if card_to_play.direct_damage:
                # direct damage BOOOIOIY!!!
                node = self.nodes[owner_alignment]["%s_%s" % (node.row, node.x)]
                if node and node.type == "unit":
                    node.unit.suffer_damage(card_to_play.direct_damage)

            if card_to_play.rubble_duration:

                node = self.nodes[owner_alignment]["%s_%s" % (node.row, node.x)]
            
                if not node:
                    # add new rubble to node
                    self.nodes[owner_alignment]["%s_%s" % (node.row, node.x)] = { type: "rubble", amount: card_to_play.rubble_duration }
                    pass
                elif node.type == "rubble":
                    # increase existing rubble (how annoying!)
                    node.amount += card_to_play.rubble_duration 

            if card_to_play.defense: 
                # it's a freaking summon!

                unit = Unit(card=card_to_play,
                        match=self.match,
                        owner_alignment=owner_alignment,
                        row=node["row"],
                        x=node["x"])

                if save_to_db:
                    unit.save()

                self.nodes[owner_alignment]["%s_%s" % (unit.row, unit.x)] = {
                    'type': "unit",
                    'unit': unit
                }




    def log(self):

        # TEMPORARY
        return

        str = ""
        for row in range(3):
            for x in range(-2, row+1): 
                if x < -row:
                    str += "   "
                elif self.nodes['ai']['%s_%s' % (row, x)]:
                    str += " %s " % self.nodes['ai']['%s_%s' % (row, x)]["unit"].damage
                else:
                    str += " - "
            logging.info(str)
            str = ""

        for inv_row in range(3):
            row = 2 - inv_row
            for x in range(-2, row+1): 
                if x < -row:
                    str += "   "
                elif self.nodes['friendly']['%s_%s' % (row, x)]:
                    str += " %s " % self.nodes['friendly']['%s_%s' % (row, x)]["unit"].damage
                else:
                    str += " - "
            logging.info(str)
            str = ""

    def load_from_session(self, session):

        match_id = session["match"]
        self.load_from_match_id(match_id)


    def load_from_match_id(self, match_id):

        for row in range(3):
            for x in range(-row, row+1): 
                self.nodes['friendly']["%s_%s" % (row, x)] = None
                self.nodes['ai']["%s_%s" % (row, x)] = None 

        self.match = Match.objects.get(id=match_id)

        units = Unit.objects.filter(match=self.match).select_related()
        for unit in units:
            self.nodes[unit.owner_alignment]["%s_%s" % (unit.row, unit.x)] = {
                'type': "unit",
                'unit': unit
            }

    def heal(self, alignment):

        for row in range(3):
            for x in range(-row, row+1): 
                node = self.nodes[alignment]["%s_%s" % (row, x)]
                if node and node["type"] == "unit":
                    unit = node["unit"]
                    unit.heal()
                else:
                    # rubble or empty
                    continue



    def do_attack_phase(self, alignment, save_to_db): 
        
        for inv_row in range(3):
            row = 2 - inv_row
            for x in range(-row, row+1): 
                node = self.nodes[alignment]["%s_%s" % (row, x)]
                if node and node["type"] == "unit":
                    self.do_attack(node["unit"], save_to_db)
                else:
                    # rubble or empty
                    continue


    def do_attack(self, unit, save_to_db):

        row = unit.row
        x = unit.x
        starting_alignment = unit.owner_alignment

        alignment = starting_alignment
        is_searching = True

        while is_searching:
            if alignment != starting_alignment:
                d_row = -1
            elif row == 2:
                d_row = 0
                if alignment == "ai": alignment = "friendly"
                else: alignment = "ai"
            else:
                d_row = 1

            row += d_row
            old_x = x

            if x != 0 and abs(x) > row:
                x = row * x / abs(x)

            if alignment == starting_alignment and unit.card.attack_type == "ranged":
                # ranged units always pass over friendly tiles, so
                # don't even worry about checking collisions
                continue

            try:
                next_node = self.nodes[alignment]["%s_%s" % (row, x)]
            except KeyError:
                next_node = None

            if next_node and next_node["type"] == "unit":
                if alignment == starting_alignment:
                    # bumped into friendly
                    return
                elif next_node and next_node["type"] == "unit":
                    # bumped into enemy unit
                    is_dead = next_node["unit"].suffer_damage(unit.card.attack, save_to_db)
                    if is_dead: 
                        # although the DB object has already been removed,
                        # we also need to remove it from the temporary
                        # data structure so we don't collide against it
                        # later in this attack phase
                        self.nodes[alignment]["%s_%s" % (row, x)] = None
                    return
                    
            elif row == 0 and x == 0:
                # bumped into enemy player

                if alignment == "ai":
                    self.match.ai_life -= unit.card.attack
                else:
                    self.match.friendly_life -= unit.card.attack

                return 


class Turn(models.Model):

    ALIGNMENT_CHOICES = (
            ("friendly", "Friendly"), 
            ("ai", "AI"),
        )

    i_win = models.BooleanField(default=False)

    play_1 = models.ForeignKey(Card, null=True)

    #this might be ignored, e.g. in the case of "all" targetting
    target_node_1 = models.ForeignKey(Node, null=True)

    is_tech_1 = models.BooleanField(default=False)

    target_alignment_1 = models.CharField(max_length=10, choices=ALIGNMENT_CHOICES)

    play_2 = models.ForeignKey(Card, null=True)

    #this might be ignored, e.g. in the case of "all" targetting
    target_node_2 = models.ForeignKey(Node, null=True)

    is_tech_2 = models.BooleanField(default=False)

    target_alignment_2 = models.CharField(max_length=10, choices=ALIGNMENT_CHOICES, null=True)


    draw_1 = models.ForeignKey(Card, null=True)
    draw_2 = models.ForeignKey(Card, null=True)




admin.site.register(Puzzle)
admin.site.register(PuzzleStartingUnit)
    
