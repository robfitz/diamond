from django.db import models

from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models.signals import post_save

from djangotoolbox.fields import ListField 

from d_cards.models import Deck


class UserProfile(models.Model):

    user = models.OneToOneField(User)

    deck = models.OneToOneField(Deck, null=True)

    beaten_puzzle_ids = ListField(models.PositiveIntegerField(), null=True, blank=True, default=[])


    def __unicode__(self):
        return self.user.username

def create_user_profile(sender, instance, created, **kwargs):

    if created:

        # extra info
        profile = UserProfile.objects.create(user=instance)

        # cards they start with
        profile.deck = Deck.create_starting_deck()
        profile.save()



post_save.connect(create_user_profile, sender=User)

admin.site.register(UserProfile)
