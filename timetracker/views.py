import sys
import re
import logging

from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import render_to_response
from django.template import RequestContext

from datetime import datetime, timedelta, date

from timetracker.models import *
from invoice.models import *


def dashboard(request):

    time_entries = TimeEntry.objects.all().order_by("start_time")
    projects = Project.objects.all()
    invoices = Invoice.objects.filter(is_default=False)

    try:
        timer_start_time = int(request.session['timer_start_time'])
    except:
        timer_start_time = None

    if timer_start_time:
        start = datetime.fromtimestamp(timer_start_time)
        delta = datetime.now() - start

        if delta.seconds > 8 * 60 * 60:
            #ignore the session if an unreasonable amount of time has
            #passed (ie more than any conceivable unbroken task)
            request.session['timer_start_time'] = None
            timer_start_time = None

    return render_to_response('dashboard.html', locals(), context_instance=RequestContext(request))


def start_task_timer(request):

    if not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])

    request.session['timer_start_time'] = request.POST.get("timer_start_time")
    return HttpResponse('ok')


def clear_task_timer(request):

    if not request.is_ajax() or not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])

    request.session['timer_start_time'] = None
    return HttpResponse('ok')


def add(request):

    if request.method == "POST":

        #clear stored timer beginning whenever a task is saved.
        #we can wipe it first since its data is duplicated in the form.
        request.session['timer_start_time'] = None

        start = None
        end = None

        text = request.POST.get("natural_text", "")
        toks = text.split()
        
        project_name = project_from_natural_text(text)
        time = time_from_natural_text(text)
        date = date_from_natural_text(text)
        description = description_from_natural_text(text)

        if time:
            time_toks = time.split("-")

            if len(time_toks) >= 2:
                #format xxxx-xxxx, with start and end specified
                start = to_datetime(time_toks[0])
                end = to_datetime(time_toks[1])

            elif len(time_toks) == 1:
                if time.startswith("-"):
                    #format -xxxx with end time specified
                    end = to_datetime(time_toks[0])
                elif time.endswith("-"):
                    #format xxxx- with start time specified
                    start = to_datetime(time_toks[0])
                else:
                    #no dashes, whole thing is our number
                    #TODO: error check this and strip non-digits
                    start = to_datetime(time_toks[0])

        timer_start = request.POST.get("start_posix")
        if not start and timer_start:
            #if start wasn't exlpicitly listed by the user, we might
            #have it available via the task timer
            start = datetime.fromtimestamp(int(timer_start))

        if not end:
            #if we don't know where the time chunk was meant to end,
            #assume the task continued until just now

            #grab the current date & time via javascript instead
            #of django so the time always reflects the users'
            #currently set time zone
            now = datetime.fromtimestamp(int(request.POST.get("now_posix")))

            #no explicit date means the task ended just now
            end = now

        duration_delta = end - start
        duration_minutes = duration_delta.seconds / 60

        if date:
            start = datetime(year=date.year,
                    month=date.month,
                    day=date.day,
                    hour=start.hour,
                    minute=start.minute)

        matching_projects = Project.objects.filter(name=project_name)
        if matching_projects.count() == 0:
            #fluidly creates new projects when a time chunk
            #is added to an unrecognized project
            project = Project(name=project_name)
            project.save()
        else:
            project = matching_projects[0]

        entry = TimeEntry(project=project,
                start_time=start,
                duration_in_minutes=duration_minutes,
                task_description=description)
        entry.save()

    return HttpResponseRedirect('/')


def project_from_natural_text(text):

    for tok in text.split():
        if not is_time_token(tok):
            #accept the first non-significant token as the project name
            return tok

    return None


def time_from_natural_text(text):

    for tok in text.split():
        if is_time_token(tok):
            return tok

    return None


def date_from_natural_text(text):

    for tok in text.split():
        if is_date_token(tok):

            date_toks = tok.split('/')
            if len(date_toks) == 2:
                #mm/dd
                return date(year=datetime.now().year, 
                        month=int(date_toks[0]),
                        day=int(date_toks[1]))

    return None


            


#all non-significant tokens after the first make up the description
def description_from_natural_text(text):

    desc = "" 
    found_project_name = False

    for tok in text.split():
        if not is_time_token(tok) and not is_date_token(tok):
            if not found_project_name:
                found_project_name = True
            elif not desc:
                desc = tok
            else:
                desc = "%s %s" % (desc, tok)

    return desc 


def is_date_token(tok):
    return tok.find("/") != -1


def is_time_token(tok):

    #00:00-00:00 with pretty much everything optional
    r = re.compile('^[0-9]{0,2}:?[0-9]{0,2}-?[0-9]{0,2}:?[0-9]{0,2}$')
    match = r.match(tok)

    return match is not None


def to_datetime(time_str):

    if time_str.find(":") != -1:
        toks = time_str.split(":")
        hour = int(toks[0])
        minute = int(toks[1])
    else:
        minute = int(time_str[-2:])
        hour = int(time_str[:-2])

    print 'hour: %s, min: %s' % (hour, minute)

    now = datetime.now()

    time = datetime(now.year, now.month, now.day, hour, minute)
    return time
