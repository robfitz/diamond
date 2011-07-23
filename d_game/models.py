import sys
import simplejson
import logging, random

from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.db import SessionStore
from django.db.models.signals import pre_save

from d_cards.models import Card, ShuffledLibrary, PuzzleDeck
from d_board.models import Node


class PuzzleStartingUnit(models.Model):

    OWNER_CHOICES = (
            ("player", "Player"), 
            ("ai", "AI"),
        )

    puzzle = models.ForeignKey("Puzzle")

    owner = models.CharField(max_length=10, default="ai")

    unit_card = models.ForeignKey(Card)
    location = models.ForeignKey(Node) 

    must_be_killed_for_victory = models.BooleanField(default=True)


    def create_unit(self, match):

        unit = Unit(card=self.unit_card,
                match=match,
                owner_alignment=self.owner,
                row=self.location.row,
                x=self.location.x,
                must_be_killed_for_puzzle_victory=self.must_be_killed_for_victory)
        unit.save()
        return unit


    def __unicode__(self):

        return "%s for %s" % (self.unit_card, self.puzzle)


class Puzzle(models.Model):

    PUZZLE_STATES = (("draft", "In Development"),
            ("submitted", "Submitted for approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"))

    GOAL = (("kill units", "Destroy enemy army"),
            ("kill player", "Kill enemy player"))

    # if a user submitted this puzzle, keep track,
    # or in case there are multiple team members working
    # on puzzles.
    creator = models.ForeignKey(User, blank=True, null=True)

    state = models.CharField(max_length=20, default="draft", choices=PUZZLE_STATES)

    # naming is mostly for admin convenience
    name = models.CharField(max_length=50, default="", blank=True)

    # sequence of puzzles you play through & progressively unlock
    order = models.DecimalField(max_digits=6, decimal_places=3)

    # whether player is trying to destroy the enemy's units,
    # kill the enemy player, or do something else (e.g. survival)
    goal = models.CharField(max_length=20, default="kill units")

    # starting life
    player_life = models.IntegerField(default=1)

    # ai starting life, which is only relevant if goal is set to "kill player",
    # since AI is unkillable in the unit destruction mode
    ai_life = models.IntegerField(default=10)

    player_cards = models.ForeignKey(PuzzleDeck, blank=True, null=True)

    intro = models.TextField(blank=True)


    class Meta:
        ordering = ['order']

    
    def can_be_edited_by(self, user):
        # can only edit puzzle decks if you're the
        # boss or if you're the user who made
        # that puzzle and it hasn't been submitted yet

        if user.is_staff:
            return True
        elif puzzle.creator == user and puzzle.state == "draft":
            return True

        return False


    def init(self, match):

        starting_units = PuzzleStartingUnit.objects.filter(puzzle=self)

        match.friendly_life = self.player_life;
        match.puzzle = self
        match.save()

        for starting_unit in starting_units:
            unit = starting_unit.create_unit(match)


    def get_setup_turn(self):

        turn = []

        for starting_unit in PuzzleStartingUnit.objects.filter(puzzle=self):
            turn.append( { 
                'card': starting_unit.unit_card.id,
                'node': starting_unit.location.id,
                'must_be_killed': starting_unit.must_be_killed_for_victory
                })

        return turn


    def __unicode__(self):

        return "%d: %s" % (self.order, self.name)


class Match(models.Model):
    """ A battle between 2 players (or a player and AI) """

    MATCH_TYPES = (
            ("puzzle", "Puzzle"), 
            ("ai", "P vs AI"),
            ("pvp", "P vs P"),
        )

    type = models.CharField(max_length=10, choices=MATCH_TYPES)

    # human who is playing in this match, or null
    # if an anon is playing
    player = models.ForeignKey(User, null=True)

    # if we don't have a real player, this'll do!
    # and it gets flipped over when they register.
    session_key = models.CharField(max_length=100)

    # if the match type is "puzzle" this will point at it
    puzzle = models.ForeignKey(Puzzle, blank=True, null=True)

    # "ai" or "friendly"
    winner = models.CharField(max_length=20, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    friendly_library = models.OneToOneField(ShuffledLibrary, null=True)
    ai_library = models.OneToOneField(ShuffledLibrary, null=True, related_name="ai_library")

    friendly_life = models.IntegerField(default=10)
    ai_life = models.IntegerField(default=10)

    friendly_tech = models.IntegerField(default=1)
    ai_tech = models.IntegerField(default=1)


    def on_unit_death(self):

        if self.type == "puzzle":

            for unit in Unit.objects.filter(match=self):

                if unit.must_be_killed_for_puzzle_victory and unit.type == "unit":
                    # at least one required unit is still alive
                    return

            # all units which should be dead are dead.. player wins!
            logging.info("@@@@ player has won")
            self.winner = "friendly"
            self.save() 


# auto-called whenever match is saved, to tell us if someone
# has won based on current life totals
def check_for_winner(sender, instance, raw, **kwargs):

    # only set winner if winner isn't already declared
    if not instance.winner:

        if instance.friendly_life <= instance.ai_life and instance.friendly_life <= 0: 
            instance.winner = "ai"

        elif instance.ai_life < instance.friendly_life and instance.ai_life <= 0: 
            instance.winner = "friendly" 

    # however winner is set (either from this function after
    # damage or directly from an alternate win condition,
    # ensure that we remember the win)
    if instance.winner == "friendly":

        if instance.type == "puzzle":

            # if we haven't already beaten this puzzle, mark that we have

            if instance.player:

                if instance.puzzle.id not in instance.player.get_profile().beaten_puzzle_ids:
                    instance.player.get_profile().beaten_puzzle_ids.append(instance.puzzle.id)
                    instance.player.get_profile().save()


pre_save.connect(check_for_winner, sender=Match)


class Unit(models.Model):
    """ A Unit is created when a card is played on the board,
        and is specific to a single match. """

    # card i represent
    card = models.ForeignKey(Card) 

    # game i'm a part of
    match = models.ForeignKey(Match)

    # "friendly" or "ai"
    owner_alignment = models.CharField(max_length=10, choices=(("friendly", "Friendly"), ("ai", "AI")))

    # location on the board
    row = models.IntegerField()
    x = models.IntegerField()

    # how much damage i've suffered
    damage = models.IntegerField(default=0)

    # once i'm dead, how much rubble i'll leave
    rubble_duration = models.IntegerField(default=1)

    must_be_killed_for_puzzle_victory = models.BooleanField(default=False)


    TYPE_CHOICES = (
            ("unit", "Unit"), 
            ("rubble", "Rubble"),
            ("empty", "Empty"),
        )

    type = models.CharField(max_length=10, default="unit", choices=TYPE_CHOICES)

    def heal(self):
        self.damage = 0
        self.save() 


    # returns true if the damage was fatal
    def suffer_damage(self, amount, save_to_db, damage_source):

        self.damage += amount

        if self.card.attack_type == "counterattack": 
            try:
                if damage_source and damage_source.card.defense and damage_source.card.attack_type != "ranged":
                    damage_source.suffer_damage(self.card.attack, save_to_db, self) 
            except:
                # not attacked by a unit, could have been plinked by spell etc
                pass

        if self.damage >= self.card.defense: 
            self.die(save_to_db)

            return True
        else:
            if save_to_db:
                self.save()

        return False


    def remove_rubble(self, amount=1):
        logging.info("**** node removing rubble from %s" % self.rubble_duration)

        if self.type != "rubble":
            return

        self.rubble_duration -= amount
        if self.rubble_duration <= 0:
            logging.info("**** node removing rubble: no more left")
            self.die()
        else:
            self.save()


    def die(self, save_to_db=True):


        become_rubble = False

        if self.type == "unit" and self.rubble_duration > 0:
            become_rubble = True 

        if self.type == "unit":
            if self.rubble_duration > 0:
                # when unit dies, it becomes rubble
                self.type = "rubble"
                if save_to_db:
                    logging.info('*** unit turned to rubble: %s' % self.type)
                    self.save()
                    self.match.on_unit_death()

            else:
                logging.info("*** unit disappeared into empty on death")
                self.type = "empty"
                if save_to_db:
                    self.save()
                    self.match.on_unit_death()
                    self.delete() 

        else:
            logging.info("*** rubble disappeared into empty")
            self.type = "empty"
            if save_to_db:
                self.save()
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
        best_target_align = None
        best_hval = -10000

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

            # test teching
            test_board.load_from_match_id(match.id)
            match.ai_tech += 1

            if is_before_attack:
                # promote offensive play by simulating
                # our AI attack
                test_board.do_attack_phase("ai", False)
            else:
                # promote more defensive play by
                # simulating the player's attack.
                test_board.cast("friendly", test_militia, None, False)
                test_board.do_attack_phase("friendly", False) 

            hval = test_board.get_ai_heuristic_value(hand_cards) 
            if hval > best_hval:
                best_hval = hval
                best_card = card
                best_target = "tech"
                best_target_align = "N/A"

            # tech back down to compensate for trying out teching
            match.ai_tech -= 1
            test_board.load_from_match_id(match.id)

            if card.tech_level > match.ai_tech:
                continue

            valid_targets = test_board.get_valid_targets_for(card, "ai")
            for target in valid_targets:
                test_board.load_from_match_id(match.id)
                test_board.cast(target.temp_alignment, card, target, False) 

                if is_before_attack:
                    # promote offensive play by simulating
                    # our AI attack
                    test_board.do_attack_phase("ai", False)
                else:
                    # if we're summoning, 
                    # promote more defensive play by
                    # simulating the player's attack.
                    test_board.cast("friendly", test_militia, None, False)
                    test_board.do_attack_phase("friendly", False) 

                hval = test_board.get_ai_heuristic_value(hand_cards)

                if hval > best_hval:
                    best_hval = hval
                    best_card = card
                    best_target = target
                    best_target_align = target.temp_alignment


        test_board.load_from_match_id(match.id)

        return { 
                'play': best_card,
                'target': best_target,
                'target_align': best_target_align
                }


    def do_turn(self, board):

        match = board.match

        if match.type == "puzzle":
            # puzzles are special turns for the AI,
            # with all the auto-steps (healing, attacking,
            # rubble) but without any casting.

            ai_turn = Turn(play_1=None,
                    target_node_1=None,
                    is_tech_1=False,
                    target_alignment_1="pass",
                    play_2=None,
                    target_node_2=None,
                    is_tech_2=False,
                    target_alignment_2="pass")

            #heal, attack, rubble
            board.heal("ai")
            board.do_attack_phase("ai", True)
            board.remove_one_rubble("ai")

            return ai_turn

        is_tech_1 = False
        is_tech_2 = False
        target_node_1 = None
        target_node_2 = None
        play_1 = None
        play_2 = None
        align_1 = None
        align_2 = None

        # ai draw
        if match.ai_library:
            match.ai_library.draw(2)

        first = self.get_play(match, True)
        logging.info("** 1st play: %s" % first)
        if first:
            play_1 = first["play"]
            target_node_1 = first["target"] 
            align_1 = first["target_align"]
            if play_1:
                match.ai_library.play(play_1.id)


        #heal and attack
        board.heal("ai")

        if not target_node_1 or target_node_1 == "tech":
            is_tech_1 = True
            target_node_1 = None

            match.ai_tech += 1
            match.save()
        else:
            board.cast(align_1, play_1, target_node_1, True)

        board.do_attack_phase("ai", True)

        second = self.get_play(match, False)
        logging.info("** 2nd play: %s" % second)
        if second:
            play_2 = second["play"]
            target_node_2 = second["target"]
            align_2 = second["target_align"]
            if play_2:
                match.ai_library.play(play_2.id)

        # ai play second card 
        if not target_node_2 or target_node_2 == "tech": 
            is_tech_2 = True
            target_node_2 = None

            match.ai_tech += 1
            match.save()
        else:
            board.cast(align_2, play_2, target_node_2, True)

        # remove ai rubble
        board.remove_one_rubble("ai")

        ai_turn = Turn(play_1=play_1,
                target_node_1=target_node_1,
                is_tech_1=is_tech_1,
                target_alignment_1=align_1,
                play_2=play_2,
                target_node_2=target_node_2,
                is_tech_2=is_tech_2,
                target_alignment_2=align_2)

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


    def remove_one_rubble(self, alignment):
        logging.info("board.remove one rubble: %s" % alignment)

        for row in range(3):
            for x in range(-row, row+1): 

                # gain points for having units
                node = self.nodes[alignment]["%s_%s" % (row, x)]

                if node and node.type == "rubble":
                    node.remove_rubble()


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

        for board_node in Node.objects.all():
            for align in simple_board:

                key = "%s_%s" % (board_node.row, board_node.x) 
                node = self.nodes[align][key]

                if not node:
                    simple_board[align][key] = {
                            'type': 'empty',
                            'node': board_node.pk,
                        }
                elif node.type == "unit":
                    simple_board[align][key] = {
                            'type': "unit",
                            'card': node.card.pk,
                            'damage': node.damage,
                            'node': board_node.pk,
                        }
                elif node.type == "rubble":
                    simple_board[align][key] = {
                            'type': "rubble",
                            'amount': node.rubble_duration,
                            'node': board_node.pk,
                        } 

        return simplejson.dumps(simple_match) 


    def get_valid_targets_for(self, card, owner_alignment):

        valid_targets = []

        enemy_alignment = "ai"
        if owner_alignment == "ai":
            enemy_alignment = "friendly"

        alignments = []
        if card.target_alignment == "any":
            alignments = ["friendly", "ai"]
        elif card.target_alignment == "friendly":
            alignments = [owner_alignment]
        elif card.target_alignment == "enemy":
            alignments = [enemy_alignment]

        for alignment in alignments:
            for node_model in Node.objects.all():
                row = node_model.row
                x = node_model.x 

                node = self.nodes[alignment]["%s_%s" % (row, x)]

                node_model.temp_alignment = alignment

                if card.target_occupant == "any":
                    valid_targets.append(node_model)
                elif card.target_occupant == "empty": 
                    if not node or node.type == "empty":
                        valid_targets.append(node_model)
                elif card.target_occupant == "rubble":
                    if node and node.type == "rubble":
                        valid_targets.append(node_model)

                elif card.target_occupant == "unit":
                    if node and node.type == "unit":
                        valid_targets.append(node_model) 

        return valid_targets


    def get_node_power(self, row, x):
        return self.node_power_levels["%s_%s" % (row, x)]

    
    def get_ai_heuristic_value(self, hand_cards): 

        
        hval = 0

        my_units = 0
        their_units = 0

        # units
        for row in range(3):
            for x in range(-row, row+1): 

                # gain points for having units
                node = self.nodes['ai']["%s_%s" % (row, x)]

                if node and node.type == 'unit': 
                    hval += node.card.unit_power_level 
                    # my_units += node.card.unit_power_level

                # lose slightly more points for enemy units
                node = self.nodes['friendly']["%s_%s" % (row, x)]
                if node and node.type == 'unit': 
                    hval -= node.card.unit_power_level * 1.1 
                    # their_units -= node.card.unit_power_level * 1.1 

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
                # my_hand+= 0.2 * card.tech_level

            # cards you can almost cast are worth a little
            elif card.tech_level == self.match.ai_tech + 1:
                hval += 0.1 * card.tech_level
                # my_hand += 0.1 * card.tech_level

        my_board = 0
        their_board = 0

        # board choices
        for row in range(3):
            for x in range(-row, row+1): 

                # lose points for having rubble
                node = self.nodes['ai']["%s_%s" % (row, x)]
                if node and node.type == 'rubble':
                    hval -= node.rubble_duration * self.node_power_levels["%s_%s" % (row, x)] * 0.33
                    # their_board -= node.rubble_duration * self.node_power_levels["%s_%s" % (row, x)] * 0.33

                # gain points for enemy rubble
                node = self.nodes['friendly']["%s_%s" % (row, x)]
                if node and node.type == 'rubble':
                    hval += node.rubble_duration * self.node_power_levels["%s_%s" % (row, x)] * 0.33
                    # my_board += node.rubble_duration * self.node_power_levels["%s_%s" % (row, x)] * 0.33

        #logging.info("@@ got heuristic: %s from life=%s/%s, hand=%s, units=%s/%s, board=%s/%s" % (hval, my_life, their_life, my_hand, my_units, their_units, my_board, their_board))

        if self.match.friendly_life <= 0:
            return hval + 1000
        elif self.match.ai_life <= 0:
            return hval - 1000
        else: return hval


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
                if save_to_db:
                    self.match.save()

            if card_to_play.direct_damage:
                # direct damage BOOOIOIY!!!
                target = self.nodes[owner_alignment]["%s_%s" % (node["row"], node['x'])]
                if target and target.type == "unit":
                    target.suffer_damage(card_to_play.direct_damage, save_to_db, card_to_play)

            if card_to_play.defense: 
                # it's a freaking summon!

                unit = Unit(card=card_to_play,
                        match=self.match,
                        owner_alignment=owner_alignment,
                        row=node["row"],
                        x=node["x"])

                if save_to_db:
                    unit.save()

                self.nodes[owner_alignment]["%s_%s" % (unit.row, unit.x)] = unit 


    def log(self):

        str = ""
        for row in range(3):
            for x in range(-2, row+1): 
                if x < -row:
                    str += "   "
                elif self.nodes['ai']['%s_%s' % (row, x)]:
                    str += " %s " % self.nodes['ai']['%s_%s' % (row, x)].damage
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
                    str += " %s " % self.nodes['friendly']['%s_%s' % (row, x)].damage
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
            self.nodes[unit.owner_alignment]["%s_%s" % (unit.row, unit.x)] = unit

    def heal(self, alignment):

        for row in range(3):
            for x in range(-row, row+1): 
                node = self.nodes[alignment]["%s_%s" % (row, x)]
                if node and node.type == "unit":
                    unit = node
                    unit.heal()
                else:
                    # rubble or empty
                    continue



    def do_attack_phase(self, alignment, save_to_db): 
        
        for inv_row in range(3):
            row = 2 - inv_row
            for x in range(-row, row+1): 
                node = self.nodes[alignment]["%s_%s" % (row, x)]
                if node and node.type == "unit":
                    self.do_attack(node, save_to_db)
                else:
                    # rubble or empty
                    continue


    def do_attack(self, unit, save_to_db):

        if unit.card.attack_type == "na" or unit.card.attack_type == "counterattack":
            # some types of units don't do anything during an active attack
            return

        row = unit.row
        x = unit.x
        starting_alignment = unit.owner_alignment

        alignment = starting_alignment
        is_searching = True

        steps_taken = 0 

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

            steps_taken += 1

            if unit.card.attack_type == "flying" and steps_taken < 3:
                # flying units skip the 2 spots in front of them
                continue

            if alignment == starting_alignment and unit.card.attack_type == "ranged":
                # ranged units always pass over friendly tiles, so
                # don't even worry about checking collisions
                continue

            try:
                next_node = self.nodes[alignment]["%s_%s" % (row, x)]
            except KeyError:
                next_node = None

            if next_node and next_node.type == "unit":
                if alignment == starting_alignment:
                    # bumped into friendly
                    return
                elif next_node and next_node.type == "unit":
                    # bumped into enemy unit
                    is_dead = next_node.suffer_damage(unit.card.attack, save_to_db, unit)
                    return
                    
            elif row == 0 and x == 0:
                # bumped into enemy player

                if alignment == "ai":
                    if self.match.type != "puzzle":
                        self.match.ai_life -= unit.card.attack
                        if save_to_db:
                            self.match.save()
                else:
                    self.match.friendly_life -= unit.card.attack
                    if save_to_db:
                        self.match.save()

                return 



class Turn(models.Model):

    ALIGNMENT_CHOICES = (
            ("friendly", "Friendly"), 
            ("ai", "AI"),
        )

    play_1 = models.ForeignKey(Card, null=True, related_name="play_1")

    #this might be ignored, e.g. in the case of "all" targetting
    target_node_1 = models.ForeignKey(Node, null=True, related_name="target_node_1")

    is_tech_1 = models.BooleanField(default=False)

    target_alignment_1 = models.CharField(max_length=10, choices=ALIGNMENT_CHOICES)

    play_2 = models.ForeignKey(Card, null=True, related_name="play_2")

    #this might be ignored, e.g. in the case of "all" targetting
    target_node_2 = models.ForeignKey(Node, null=True, related_name="target_node_2")

    is_tech_2 = models.BooleanField(default=False)

    target_alignment_2 = models.CharField(max_length=10, choices=ALIGNMENT_CHOICES, null=True)


    draw_1 = models.ForeignKey(Card, null=True, related_name="draw_1")
    draw_2 = models.ForeignKey(Card, null=True, related_name="draw_2")


class PuzzleStartingUnitAdmin(admin.ModelAdmin):

    list_display_links = ("__unicode__",)
    list_display = ("__unicode__", "owner")
    list_editable = ("owner",)


class PuzzleAdmin(admin.ModelAdmin):

    list_display_links = ("__unicode__",)
    list_display = ("__unicode__", "name", "order", "player_life", "player_cards", "intro", "state")
    list_editable = ("name", "order", "player_life", "player_cards", "intro", "state")


admin.site.register(PuzzleStartingUnit, PuzzleStartingUnitAdmin) 

admin.site.register(Puzzle, PuzzleAdmin)
