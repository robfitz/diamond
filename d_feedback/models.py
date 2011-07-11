from django.db import models
from django.forms import ModelForm
from django.contrib import admin

from d_game.models import Match, Puzzle


class PuzzleFeedback(models.Model): 

    DIFFICULTY_CHOICES = (
            ("no opinion", "No opinion"),
            ("confused", "I'm so confused"),
            ("boring", "Boring"),
            ("easy", "Easy"),
            ("average", "Average"),
            ("interesting", "Interesting!"),
            ("impossible", "It may actually be impossible"),
        )

    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, blank=False, default="no opinion", verbose_name="Puzzle difficulty")

    feedback = models.TextField(blank=True, verbose_name="Other thoughts?")

    # id of the match which was played, in case we want
    # to find the players or decks or whatever
    match = models.ForeignKey(Match, blank=True, null=True)

    # which puzzle this feedback refers to
    puzzle = models.ForeignKey(Puzzle, blank=True, null=True)

    # when this feedback was submitted
    timestamp = models.DateTimeField(auto_now_add=True)


class PuzzleFeedbackForm(ModelForm):
    pass

    class Meta:
        model = PuzzleFeedback
        exclude = ('match', 'puzzle', 'timestamp')

admin.site.register(PuzzleFeedback)
