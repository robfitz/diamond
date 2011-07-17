import logging

from django.shortcuts import render_to_response
from django.contrib.auth.models import User

from d_users import util as users_util
from d_metrics.models import UserMetrics
from d_game.models import Match


def user_metrics(request):

    init_user_metrics()
    cache_user_metrics(request)

    all_user_metrics = UserMetrics.objects.all()

    activation_range = range(UserMetrics().total_activation_funnel_steps)
    acquisition_range = range(UserMetrics().total_acquisition_funnel_steps)

    return render_to_response("metrics/users.html", locals())


def cache_user_metrics(request):


    for metrics in UserMetrics.objects.all():

        metrics.anon_session_key
        beaten_puzzle_ids = users_util.unique_puzzles_won(metrics.user, metrics.anon_session_key)

        if metrics.user: 
            begun = Match.objects.filter(player=metrics.user).filter(type='ai')

        else:
            begun = Match.objects.filter(session_key=request.session.session_key).filter(type='ai')

        metrics.unique_puzzles_won = len(beaten_puzzle_ids)

        metrics.total_ai_matches_begun = begun.count()
        metrics.total_ai_matches_won = begun.filter(winner="friendly").count()
        metrics.total_ai_matches_lost = begun.filter(winner="ai").count()

        metrics.total_cards_earned = 0 

        metrics.save()


def init_user_metrics():

    # user_metrics are the only way we have to track
    # the happenings of anon sessions, so we can't
    # do anything about recovering that data. 
    # however, we can still work backward frome existing
    # user accounts and fill in most of the pieces there
    
    for user in User.objects.all():

        try:
            m = UserMetrics.objects.get(user=user)
            pass
        except: 
            # init metrics 
            metrics = UserMetrics(user=user,
                    first_visit_date=None,
                    signup_date=user.get_profile().signup_date,
                    first_visit_version=0,
                    signup_version=0) 

            metrics.save() 
            metrics.first_visit_date = None
            metrics.save()
