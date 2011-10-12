import sys
import simplejson
import logging, random

from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.db import SessionStore
from django.db.models.signals import pre_save
from djangotoolbox.fields import ListField 

from d_cards.models import Card, PuzzleDeck
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

    GOAL_TYPES = (
            ("kill player", "Kill player"), 
            ("kill units", "Kill units"),
        )

    log = models.TextField(default="")

    type = models.CharField(max_length=20, choices=MATCH_TYPES)
    goal = models.CharField(max_length=20, choices=GOAL_TYPES)

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

    friendly_deck_cards = ListField(models.IntegerField())
    ai_deck_cards = ListField(models.IntegerField())

    friendly_life = models.IntegerField(default=1)
    ai_life = models.IntegerField(default=1)

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
admin.site.register(Match)
