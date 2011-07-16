from django.db import models
from django.contrib.auth.models import User
from djangotoolbox.fields import ListField 


class UserMetrics(models.Model):

    user = models.OneToOneField(User, null=True, related_name="metrics")
    anon_session_key = models.CharField(max_length=50)

    first_visit_date = models.DateTimeField(auto_now_add=True, null=True) 
    signup_date = models.DateTimeField(null=True)

    first_visit_version = models.IntegerField() 
    signup_version = models.IntegerField()

    login_dates = ListField(models.DateField(), default=[])

    unique_puzzles_won = models.IntegerField(default=0)
    
    total_ai_matches_begun = models.IntegerField(default=0)
    total_ai_matches_lost = models.IntegerField(default=0)
    total_ai_matches_won = models.IntegerField(default=0) 

    total_cards_earned = models.IntegerField(default=0)


    def seven_day_activity_percent(self):

        active_days = 0

        for login_date in self.login_dates[-7:]:

            pass

        return "TODO" 


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



    

    
    
    

    



