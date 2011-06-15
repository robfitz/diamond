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

    name = models.CharField(max_length=20, blank=True)

    # whether it targets your units or enemy units.
    # rubble is a special case since it is usually on the opposite side
    # (e.g. the enemy's rubble is on your playfield)
    alignment = models.CharField(max_length=10, choices=ALIGNMENT_CHOICES)

    # whether an unit should be on top of that square or not
    occupant = models.CharField(max_length=10, choices=OCCUPANT_CHOICES)

    # how to decide where to apply the effect, whether through user choice or otherwise.
    # locations only apply to valid targets according to 'alignment' and 'occupant',
    location = models.CharField(max_length=10, choices=LOCATION_CHOICES)


    def __unicode__(self):
        if self.name:
            return "%s (%s %s %s)" % (self.name, self.alignment, self.occupant, self.location)
        else:
            return "%s %s %s" % (self.alignment, self.occupant, self.location)


class Unit(models.Model):

    ATTACK_CHOICES = (
            ("melee", "Melee"),
            ("ranged", "Ranged"),
            ("defender", "Defender"),
            ("wall", "Wall"),
        )

    name = models.CharField(max_length=20, blank=True)

    #how much damage this unit deals to a player or unit each time it attacks
    attack = models.IntegerField(default=1)

    #how much damage in a single turn is needed to destroy this unit
    defense = models.IntegerField(default=1)

    # offensive behaviour:
    ## melee runs forward until it hits any obstacle, attacking if it meets an enemy unit first. 
    ## ranged passes over friendly units & rubble to hit the first hostile ones. 
    ## defenders counter-attack anything that strikes them, but don't actively attack
    ## on their own
    attack_type = models.CharField(max_length=10, choices=ATTACK_CHOICES, default="melee")


    def __unicode__(self):
        return "%s %s/%s %s" % (self.name, self.attack, self.defense, self.attack_type)


class Card(models.Model):

    # where/how this card can be played
    targetting = models.ForeignKey(Targetting)

    # which unit it summons, if any
    summon = models.ForeignKey(Unit, null=True, blank=True, help_text="Which unit (if any) you want to appear in the targetted spaces")

    # which tech level you need to be at in order to play this card.
    # should generally be either 1, 3, or 5.
    tech_level = models.IntegerField(default=1, help_text="Player must have reached this tech level in order to use the card")

    # how much playing this card changes your current tech level (usually ranging from -2 to +2)
    tech_change = models.IntegerField(default=0, help_text="If non-zero, it will change the player's current tech level by that positive or negative amount.")

    #if it hits a unit, how much should it change the thing's health (positive heals, negative damages)
    health_change = models.IntegerField(default=0, help_text="How much damage you want to do to any units on the targetted spaces. Positive values heal, negative ones hurt. Large negative values will insta-kill.")

    # rubble decays over time. if positive, and if there is no unit on the affected node
    # after the effect ends, rubble of this quantity will be placed there.
    # in this case of a rubble collision, they do not add, but instead the node is set to the 
    # value of the larger rubble.
    rubble_duration = models.IntegerField(default=0, help_text="How many turns to leave rubble in the targetted spaces, but ONLY IF the space is empty after other effects have triggered (e.g. a summon plus a rubble would perform the summon but not the rubble. A damage 3 plus rubble will only add the rubble if the unit dies.")


    def __unicode__(self):

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

        if self.rubble_duration:
            str += "Rubble %s." % self.rubble_duration 

        return str


    
admin.site.register(Targetting)
admin.site.register(Unit)
admin.site.register(Card) 
