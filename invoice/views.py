import sys
import re
import logging

from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.core.mail import send_mail

from datetime import datetime

from timetracker.models import *
from invoice.models import *


def view_invoice(request, invoice_key):

    invoice = get_object_or_404(Invoice, key=invoice_key)
    project = invoice.project
    client = project.client

    return render_to_response("invoice/invoice.html", locals())


def create_invoice(request, project_id):

    project = get_object_or_404(Project, id=project_id)

    invoice = Invoice.create(project)

    return HttpResponseRedirect('/invoice/%s/' % invoice.key)


def send_invoice(request, invoice_id):

    invoice = get_object_or_404(Invoice, id=invoice_id)
    project = invoice.project
    client = project.client

    subject = "Invoice for %s" % invoice.project.name
    from_email = "robftz@gmail.com"
    to_email = client.contact_email
    message = """Hello %(contact_name)s

Here's the latest invoice for %(project_name)s:
%(invoice_url)s

The time count is %(invoice_hours)s hours. A full task breakdown is at:
%(timesheet_url)s

Give me a shout if you've got any questions or issues.

Best,
Rob""" % { 
        'contact_name': client.contact_name,
        'invoice_hours': invoice.hours(),
        'project_name': project.name,
        'invoice_url': request.build_absolute_uri('/invoice/%s/' % invoice.key),
        'timesheet_url': request.build_absolute_uri('/invoice/%s/timesheet/' % invoice.key)
        }

    send_mail(subject, message, from_email, [to_email, 'robftz@gmail.com'], fail_silently=False)

    return HttpResponseRedirect('/')
