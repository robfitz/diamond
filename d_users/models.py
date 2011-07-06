from django.db import models

from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models.signals import post_save

class UserProfile(models.Model):

    user = models.OneToOneField(User)


    def __unicode__(self):
        return self.user.username

def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


post_save.connect(create_user_profile, sender=User)

admin.site.register(UserProfile)
