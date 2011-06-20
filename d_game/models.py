import logging
from django.db import models

from d_cards.models import Card
from d_board.models import Node


class Match(models.Model):

    winner = models.CharField(max_length=20, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)


class Unit(models.Model):

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



class Board():

    nodes = { 'friendly': { }, 'ai': { } }


    def log(self):

        logging.info("AI")
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

        logging.info("")

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
        logging.info("Friendly")

    def load_from_session(self, session):

        for row in range(3):
            for x in range(-row, row+1): 
                self.nodes['friendly']["%s_%s" % (row, x)] = None
                self.nodes['ai']["%s_%s" % (row, x)] = None 

        match_id = session["match"]

        units = Unit.objects.filter(match__id=match_id).select_related()
        for unit in units:
            self.nodes[unit.owner_alignment]["%s_%s" % (unit.row, unit.x)] = {
                'type': "unit",
                'unit': unit
            }


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
                return
    


class Turn(models.Model):

    #match = models.ForeignKey(Match)

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



    
