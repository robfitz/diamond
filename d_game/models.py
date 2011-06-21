import logging, random
from django.db import models

from d_cards.models import Card, ShuffledLibrary
from d_board.models import Node



class Match(models.Model):
    """ A battle between 2 players (or a player and AI) """

    winner = models.CharField(max_length=20, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    friendly_library = models.OneToOneField(ShuffledLibrary)
    ai_library = models.OneToOneField(ShuffledLibrary)

    friendly_life = models.IntegerField(default=10)
    ai_life = models.IntegerField(default=10)

    friendly_tech = models.IntegerField(default=1)
    ai_tech = models.IntegerField(default=1)



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
    def suffer_damage(self, amount):
        self.damage += amount
        if self.damage >= self.card.defense:
            logging.info("&& unit suffer damage and died: %s" % amount)
            self.die()
            return True
        logging.info("&& unit suffer damage: %s" % amount)
        return False


    def die(self):
        self.delete()



class AI():
    """ AI player logic who decides what to play and do """
    
    def do_turn(self, match, board):

        # ai draw
        match.ai_library.draw(2)

        logging.info("^^ ai hand: %s" % match.ai_library.hand_card_ids)

        hand_cards = match.ai_library.hand_cards()
        play_1 = random.choice(hand_cards)
        match.ai_library.play(play_1.id)

        hand_cards = match.ai_library.hand_cards()
        play_2 = random.choice(hand_cards)
        match.ai_library.play(play_2.id)

        logging.info("** chose cards to play")

        target_node_1 = None
        target_node_2 = None
        is_tech_1 = False
        is_tech_2 = False

        logging.info("BOARD BEFORE AI HEAL")
        board.log()

        #heal and attack
        board.heal("ai")

        logging.info("BOARD AFTER AI HEAL")
        board.log()

        # ai play first card
        if play_1.tech_level <= match.ai_tech:
            for row in range(3):
                if target_node_1:
                    break
                for x in range(-row, row+1): 
                    if not board.nodes["ai"]["%s_%s" % (row, x)]:
                        target_node_1 = Node.objects.get(row=row,x=x)
                        break
                    
        if not target_node_1:
            logging.info("** ai 1st cast: teching")
            is_tech_1 = True
            target_node_1 = None
        else:
            board.cast("ai", play_1, target_node_1)

        logging.info("BOARD AFTER AI CAST 1")
        board.log()

        board.do_attack_phase("ai")

        logging.info("BOARD AFTER AI ATTACK")
        board.log()

        # ai play second card
        if play_2.tech_level <= match.ai_tech:
            for row in range(3):
                if target_node_2:
                    break
                for x in range(-row, row+1): 
                    if not board.nodes["ai"]["%s_%s" % (row, x)]:
                        target_node_2 = Node.objects.get(row=row,x=x)
                        break

        if not target_node_2: 
            logging.info("** ai 2nd cast: teching")
            is_tech_2 = True
            target_node_2 = None
        else:
            board.cast("ai", play_2, target_node_2)

        logging.info("BOARD AFTER AI CAST 2")
        board.log()

        logging.info("** chose targets")

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

    def cast(self, owner_alignment, card_to_play, node_to_target):

        logging.info("** pre-cast: played card node %s %s to: %s" % (node_to_target.row, node_to_target.x, card_to_play.pk))

        unit = Unit(card=card_to_play,
                match=self.match,
                owner_alignment=owner_alignment,
                row=node_to_target.row,
                x=node_to_target.x)
        unit.save()

        if card_to_play.target_aiming == 'chosen':
            self.nodes[owner_alignment]["%s_%s" % (unit.row, unit.x)] = {
                'type': "unit",
                'unit': unit
            }
        elif card_to_play.target_aiming == 'all':
            for row in range(3):
                for x in range(-row, row+1): 
                    if not self.nodes[owner_alignment]["%s_%s" % (row, x)]:
                        self.nodes[owner_alignment]["%s_%s" % (row, x)] = {
                            'type': "unit",
                            'unit': unit
                        }

        logging.info("** cast: played card node %s %s to: %s" % (node_to_target.row, node_to_target.x, card_to_play.pk))



    def log(self):

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

        for row in range(3):
            for x in range(-row, row+1): 
                self.nodes['friendly']["%s_%s" % (row, x)] = None
                self.nodes['ai']["%s_%s" % (row, x)] = None 

        match_id = session["match"]
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
                logging.info("%s" % node)
                if node and node["type"] == "unit":
                    unit = node["unit"]
                    unit.heal()



    def do_attack_phase(self, alignment): 
        
        for row in range(3):
            for x in range(-row, row+1): 
                node = self.nodes[alignment]["%s_%s" % (row, x)]
                logging.info("%s" % node)
                if node and node["type"] == "unit":
                    self.do_attack(node["unit"])
                else:
                    # rubble or empty
                    continue


    def do_attack(self, unit):

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
                    is_dead = next_node["unit"].suffer_damage(unit.card.attack)
                    if is_dead: 
                        # although the DB object has already been removed,
                        # we also need to remove it from the temporary
                        # data structure so we don't collide against it
                        # later in this attack phase
                        self.nodes[alignment]["%s_%s" % (row, x)] = None
                    return
                    
            elif row == 0 and x == 0:
                # bumped into enemy player

                logging.info("## damaged player %s for %s" % (alignment, unit.card.attack))

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

    play_1 = models.ForeignKey(Card)

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



    
