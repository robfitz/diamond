import logging
from datetime import date

from django.db import models
from django.contrib.auth.models import User
from djangotoolbox.fields import ListField 
from django.contrib import admin


class UserMetrics(models.Model):

    user = models.OneToOneField(User, null=True, related_name="metrics")
    anon_session_key = models.CharField(max_length=50)

    first_visit_date = models.DateTimeField(auto_now_add=True, null=True) 
    signup_date = models.DateTimeField(null=True)

    first_visit_version = models.IntegerField(default=0) 
    signup_version = models.IntegerField(default=0)

    login_dates = ListField(models.DateField(), default=[])

    unique_puzzles_won = models.IntegerField(default=0)
    
    total_ai_matches_begun = models.IntegerField(default=0)
    total_ai_matches_lost = models.IntegerField(default=0)
    total_ai_matches_won = models.IntegerField(default=0) 

    total_cards_earned = models.IntegerField(default=0)


    def seven_day_activity_percent(self):

        active_days = 0 
        today = date.today()

        max_days = 7
        # if self.first_visit_date:
            # max_days = (today - self.first_visit_date).days + 1
            # if max_days > 7: 
                # max_days = 7
        # else:
            # max_days = 7 


        for login_date in self.login_dates[-max_days:]:
            delta = today - login_date
            if delta.days >= max_days:
                break
            else: 
                active_days += 1 

        return 100 * active_days / max_days 


    def activation_funnel_percent(self):

        total_steps = 2
        completed = 0

        if self.user:
            # has made an account 
            completed += 1

            if self.user.email:
                # has opted in for marketing
                completed += 1

        return 100 * completed / total_steps 


    def acquisition_funnel_percent(self):

        total_steps = 4
        completed = 0

        # by virtue of this user being tracked,
        # they have arrived on the page so
        completed += 1

        if self.unique_puzzles_won > 1:
            # has beaten a puzzle
            completed += 1

            if self.total_cards_earned > 1:
                # has earned a card
                completed += 1

                if self.total_deck_edits > 1:
                    # has saved a new deck
                    completed += 1

        return 100 * completed / total_steps 



admin.site.register(UserMetrics)
