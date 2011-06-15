from django.db import models
from django.contrib import admin


class Targetting(models.Model):
    ALIGNMENT_CHOICES = (
            ("friendly", "Friendly"), 
            ("enemy", "Enemy"),
            ("any", "Any")
        )
    OCCUPANT_CHOICES = (
            ("occupied", "Occupied"), 
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
    alignment = models.CharField(max_length=10, choices=ALIGNMENT_CHOICES)

    # whether an unit should be on top of that square or not
    occupant = models.CharField(max_length=10, choices=OCCUPANT_CHOICES)

    # how to decide where to apply the effect, whether through user choice or otherwise.
    # locations only apply to valid targets according to 'alignment' and 'occupant',
    location = models.CharField(max_length=10, choices=LOCATION_CHOICES)


class Unit(models.Model):

    ATTACK_CHOICES = (
            ("melee", "Melee"),
            ("ranged", "Ranged"),
            ("defender", "Defender")
        )


    #how much damage this unit deals to a player or unit each time it attacks
    attack = models.IntegerField(default=1)

    #how much damage in a single turn is needed to destroy this unit
    defense = models.IntegerField(default=1)

    # offensive behaviour:
    ## melee runs forward until it hits any obstacle, attacking if it meets an enemy unit first. 
    ## ranged passes over friendly units & rubble to hit the first hostile ones. 
    ## defenders counter-attack anything that strikes them, but don't actively attack
    ## on their own
    attack_type = models.CharField(max_length=10, choices=ATTACK_CHOICES)



class Card(models.Model):

    # where/how this card can be played
    targetting = models.ForeignKey(Targetting)

    # which unit it summons, if any
    summons = models.ForeignKey(Unit, null=True, blank=True)

    # which tech level you need to be at in order to play this card.
    # should generally be either 1, 3, or 5.
    tech_level = models.IntegerField(default=1)

    # how much playing this card changes your current tech level (usually ranging from -2 to +2)
    tech_change = models.IntegerField(default=0)

    #if it hits a unit, how much should it change the thing's health (positive heals, negative damages)
    health_change = models.IntegerField(default=0)

    # rubble decays over time. if positive, and if there is no unit on the affected node
    # after the effect ends, rubble of this quantity will be placed there.
    # in this case of a rubble collision, they do not add, but instead the node is set to the 
    # value of the larger rubble.
    rubble_duration = models.IntegerField(default=0)

    
admin.site.register(Targetting)
admin.site.register(Unit)
admin.site.register(Card) 
