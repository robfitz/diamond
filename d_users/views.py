import logging
from datetime import datetime

from settings import VERSION
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect

from django.contrib.auth.models import User
from django.contrib import auth

from d_game.models import Match
from d_metrics.models import UserMetrics


def register(request):

    next = "/"
    errors = ""

    if request.method == "POST":

        pre_login_session_key = request.session.session_key

        username = request.POST.get("username")

        if User.objects.filter(username=username).exists():
            errors = "That username has already been taken. If that's your account, try logging in instead. Otherwise, try creating an account with a different username"

        else:
            pw1 = request.POST.get("password_1")
            pw2 = request.POST.get("password_2") 

            if pw1 and pw1 != pw2:
                errors = "Passwords don't match. Typo?"

            else:
                email = request.POST.get("email", "")
                user = User.objects.create_user(username, email=email, password=pw1)
                user = auth.authenticate(username=username, password=pw1)
                if user: 
                    auth.login(request, user) 

                    # attach any session state to this new account 
                    init_winnings(user, pre_login_session_key) 
                    init_metrics(user, pre_login_session_key)

                    return HttpResponseRedirect(request.POST.get("next"))


    return render_to_response("registration/register.html", locals(), context_instance=RequestContext(request))


def init_metrics(user, pre_login_session_key):

    try:
        metrics = UserMetrics.objects.get(anon_session_key=pre_login_session_key)
        
    except:
        # they apparently logged in before doing ANYTHING, so
        # create new metrics for them
        metrics = UserMetrics(user=user)

    metrics.user = user
    metrics.signup_version = VERSION
    metrics.signup_date = datetime.now()

    metrics.save() 


def init_winnings(user, pre_login_session_key):

    beaten_matches = Match.objects.filter(session_key=pre_login_session_key)
    logging.info("@@@ beaten matches: %s" % beaten_matches)
    beaten_puzzle_ids = []
    for match in beaten_matches:
        if match.type == "puzzle" and match.winner == "friendly" and match.puzzle.id not in beaten_puzzle_ids:
            beaten_puzzle_ids.append(match.puzzle.id)

        # update from pointing to an outdated session key
        # to pointing at a real live user
        match.player = user
        match.save()

    user.get_profile().beaten_puzzle_ids = beaten_puzzle_ids
    user.get_profile().save()
