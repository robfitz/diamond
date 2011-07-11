import random
import logging

from django import forms
from django.db import models
from django.core import serializers
from django.contrib import admin
from djangotoolbox.fields import ListField 
from django.db.models.signals import pre_save


class Card(models.Model):

    name = models.CharField(max_length="20", blank=True)
    
    unit_power_level = models.IntegerField(default=0)

    ATTACK_CHOICES = (
            ("na", "N/A"),
            ("melee", "Melee"),
            ("ranged", "Ranged"),
            ("defender", "Defender"),
            ("wall", "Wall"),
        )

    name = models.CharField(max_length=20, blank=True)

    tooltip = models.CharField(max_length=200, blank=True, default="")

    icon_url = models.CharField(max_length=200, blank=True, default="")
    icon_url_back = models.CharField(max_length=200, blank=True, default="")

    #how much damage this unit deals to a player or unit each time it attacks
    attack = models.IntegerField(default=1, help_text="If this card summons a unit, how much damage it can deal per attack")

    #how much damage in a single turn is needed to destroy this unit
    defense = models.IntegerField(default=1, help_text="If this card summons a unit, how much damage it can endure per turn")

    # offensive behaviour:
    ## melee runs forward until it hits any obstacle, attacking if it meets an enemy unit first. 
    ## ranged passes over friendly units & rubble to hit the first hostile ones. 
    ## defenders counter-attack anything that strikes them, but don't actively attack
    ## on their own
    attack_type = models.CharField(max_length=10, choices=ATTACK_CHOICES, default="na", help_text="If this card summons a unit, how it behaves during an attack (e.g. ranged, melee, defender..)")

    # which tech level you need to be at in order to play this card.
    # should generally be either 1, 3, or 5.
    tech_level = models.IntegerField(default=1, help_text="Player must have reached this tech level in order to use the card")

    # how much playing this card changes your current tech level (usually ranging from -2 to +2)
    tech_change = models.IntegerField(default=0, help_text="If non-zero, it will change the player's current tech level by that positive or negative amount.")

    ALIGNMENT_CHOICES = (
            ("friendly", "Friendly"), 
            ("enemy", "Enemy"),
            ("any", "Any")
        )
    OCCUPANT_CHOICES = (
            ("unit", "Unit"),
            ("rubble", "Rubble"),
            ("empty", "Empty"),
            ("any", "Any")
        )
    LOCATION_CHOICES = (
            ("chosen", "Chosen"),
            ("random", "Random"),
            ("all", "All")
        )

    # whether it targets your units or enemy units.
    # rubble is a special case since it is usually on the opposite side
    # (e.g. the enemy's rubble is on your playfield)
    target_alignment = models.CharField(max_length=10, choices=ALIGNMENT_CHOICES, default="friendly")

    # whether an unit should be on top of that square or not
    target_occupant = models.CharField(max_length=10, choices=OCCUPANT_CHOICES, default="empty")

    # how to decide where to apply the effect, whether through user choice or otherwise.
    # locations only apply to valid targets according to 'alignment' and 'occupant',
    target_aiming = models.CharField(max_length=10, choices=LOCATION_CHOICES, default="chosen")

    # how much damage to do (or heal) a unit for
    direct_damage = models.IntegerField(default=0)

    def __unicode__(self):

        if self.name:
            return "T%s: %s" % (self.tech_level, self.name)

        str = "T%s" % self.tech_level

        if self.tech_change < 0:
            str += " (%s)" % self.tech_change
        elif  self.tech_change > 0:
            str += " (+%s)" % self.tech_change
        str += ": "

        if self.summon:
            str += "Summon" 
            if self.summon.name:
                str += " %s. " % self.summon.name
            else:
                str += ". "

        if self.health_change < 0:
            str += "Damage %s. " % -self.health_change
        elif self.health_change > 0:
            str += "Heal %s. " % self.health_change

        return str


def set_tooltip(sender, instance, raw, **kwargs):

    instance.tooltip = "<b>T%s: %s</b><br/>" % (instance.tech_level, instance.name)

    if instance.defense:
        instance.tooltip += "%s/%s %s" % (instance.attack, instance.defense, instance.attack_type)
    if instance.direct_damage:
        instance.tooltip += "%s direct damage" % (instance.direct_damage)

    if instance.target_aiming == "all":
        tar = None 
        if instance.target_occupant == "empty":
            tar = "empty spaces"
        elif instance.target_occupant == "unit":
            tar = "units"
        elif instance.target_occupant == "any":
            tar = "nodes"
        elif instance.target_occupant == "rubble":
            tar = "rubble"
        instance.tooltip += " to all %s %s" % (instance.target_alignment, tar)
    elif instance.target_alignment == "friendly" and instance.target_occupant == "empty":
        # basic summon doesn't need to be described
        pass
    else: 
        instance.tooltip += " to %s %s" % (instance.target_alignment, instance.target_occupant)

    instance.tooltip += "<br/>"

    if instance.defense:
        # extra info about the attack type of units,
        # in lieu of a proper tutorial

        instance.tooltip += "<br/>"
        if instance.attack_type == "melee":
            instance.tooltip += "Melee units move forward until they reach any unit, friendly or otherwise.<br/>"

        if instance.attack_type == "ranged":
            instance.tooltip += "Ranged units shoot over friendly units to hit the first enemy in front of them.<br/>"

        if instance.attack_type == "flying":
            instance.tooltip += "Flying units skip over exactly 2 spaces in front of them, and then attack the next unit.<br/>"


pre_save.connect(set_tooltip, sender=Card)


class CardAdmin(admin.ModelAdmin):
    list_display_links = ('__unicode__',)
    list_display = ('__unicode__', 'tech_level', 'name', 'attack', 'defense', 'attack_type', 'unit_power_level', 'target_alignment', 'target_occupant', 'target_aiming', 'direct_damage', 'icon_url', 'icon_url_back')
    list_editable = ('name', 'tech_level', 'attack', 'defense', 'attack_type', 'unit_power_level', 'target_alignment', 'target_occupant', 'target_aiming', 'direct_damage', 'icon_url', 'icon_url_back')


class ShuffledLibrary(models.Model):

    undrawn_card_ids = ListField(models.PositiveIntegerField(), null=True, blank=True, default=[])

    hand_card_ids = ListField(models.PositiveIntegerField(), null=True, blank=True, default=[])


    def hand_cards(self):

        all_cards = Card.objects.all()
        cards = []

        for card_id in self.hand_card_ids:
            card = Card.objects.get(id=card_id)
            cards.append(card)

        return cards


    def play(self, card_id):

        logging.info("$$$ lib.play() %s, %s" % (card_id, self.hand_card_ids))

        if card_id in self.hand_card_ids:

            index = self.hand_card_ids.index(card_id)
            logging.info("$$$ %s" % index)
            del(self.hand_card_ids[index])
            logging.info("$$$ after del: %s" % self.hand_card_ids)
            self.save() 

            # successfully removed the card from our hand
            return True

        # the card that was played isn't actually
        # in our hand, so return failure
        return False


    def draw_as_json(self, num):

        card_ids = self.draw(num)
        logging.info("** library.draw json: %s" % card_ids)

        hand = []

        for id in card_ids:
            card = Card.objects.get(id=id)
            hand.append(card) 

        hand_json = serializers.serialize("json", hand)

        return hand_json
        

    def draw(self, num):

        if num <= 0:
            return []

        to_draw = self.undrawn_card_ids[:num]

        # remove cards from undrawn pile
        self.undrawn_card_ids = self.undrawn_card_ids[num:]

        # add cards to hand
        for card in to_draw:
            self.hand_card_ids.append(card) 


        self.save()

        return to_draw 

    
    def init(self, deck, is_shuffled=True):

        # create a clean copy
        if deck:
            self.undrawn_card_ids = list(deck.card_ids) 
        else:
            self.undrawn_card_ids = []

        if is_shuffled:
            # shuffle
            random.shuffle(self.undrawn_card_ids)

        self.save()

        return self


class Deck(models.Model):

    nickname = models.CharField(max_length=50)

    card_ids = ListField(models.PositiveIntegerField(), null=True, blank=True)
    max_size = models.IntegerField(default=20)

    def create_starting_deck():

        starting_deck = Deck(nickname="Soldiers 'n archers")

        try:
            soldier = Card.objects.filter(attack=1, defense=2, attack_type="melee", tech_level=1)[0]
            archer = Card.objects.filter(attack=1, defense=1, attack_type="ranged", tech_level=1)[0]

            starting_deck.card_ids = [soldier.id, soldier.id, soldier.id, soldier.id, archer.id, archer.id, archer.id] 
        except:
            starting_deck.card_ids = []

        starting_deck.save() 
        return starting_deck

    create_starting_deck = staticmethod(create_starting_deck)

    def all_cards(self):
        if not self.card_ids:
            return []

        cards = Card.objects.all()
        with_duplicates = []
        for id in self.card_ids:
            with_duplicates.append(cards.get(id=id))
        return with_duplicates 

    def __unicode__(self):

        return "%s %s" % (self.id, self.nickname)

    
admin.site.register(Card, CardAdmin) 
admin.site.register(Deck)
