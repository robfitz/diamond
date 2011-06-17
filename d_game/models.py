from django.db import models

from d_cards.models import Card
from d_board.models import Node


class Match(models.Model):

    winner = models.CharField(max_length=20, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)


class Turn(models.Model):

    #match = models.ForeignKey(Match)

    ALIGNMENT_CHOICES = (
            ("friendly", "Friendly"), 
            ("enemy", "Enemy"),
        )

    i_win = models.BooleanField(default=False)

    play_1 = models.ForeignKey(Card)

    #this might be ignored, e.g. in the case of "all" targetting
    target_node_1 = models.ForeignKey(Node, null=True)

    target_alignment_1 = models.CharField(max_length=10, choices=ALIGNMENT_CHOICES)

    play_2 = models.ForeignKey(Card, null=True)

    #this might be ignored, e.g. in the case of "all" targetting
    target_node_2 = models.ForeignKey(Node, null=True)

    target_alignment_2 = models.CharField(max_length=10, choices=ALIGNMENT_CHOICES, null=True)


    draw_1 = models.ForeignKey(Card, null=True)
    draw_2 = models.ForeignKey(Card, null=True)



    
