import logging

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect

from django.contrib.auth.models import User
from django.contrib import auth


def register(request):

    next = "/"
    errors = ""

    if request.method == "POST":

        username = request.POST.get("username")

        if User.objects.filter(username=username).exists():
            errors = "That username has already been taken. If that's your account, try logging in instead. Otherwise, try creating an account with a different username"

        else:
            pw1 = request.POST.get("password_1")
            pw2 = request.POST.get("password_2") 

            if pw1 and pw1 != pw2:
                errors = "Passwords don't match. Typo?"

            else:
                user = User.objects.create_user(username, email=username, password=pw1)
                user = auth.authenticate(username=username, password=pw1)
                if user: 
                    auth.login(request, user) 
                    return HttpResponseRedirect(request.POST.get("next"))


    return render_to_response("registration/register.html", locals(), context_instance=RequestContext(request))
