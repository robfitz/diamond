from django.db import models
from django.contrib import admin

from timetracker.models import Project
from utils.util import rand_key

from datetime import timedelta

class TimeEntry(models.Model):

    project = models.ForeignKey(Project)
    start_time = models.DateTimeField()
    duration_in_minutes = models.IntegerField()
    task_description = models.CharField(max_length="120", default="", blank=True)

    #since nonrel can't query for null foreign keys, we set to a default invoice
    #with pk=1 which is loaded via intial_data fixture
    invoice = models.ForeignKey("Invoice", default="1", null=True)


    def __unicode__(self):

        return "TimeEntry for %s on %s for %sm" % (self.project.name, self.start_time, self.duration_in_minutes)


    def end_time(self):
        delta = timedelta(minutes=self.duration_in_minutes)
        return self.start_time + delta


class Invoice(models.Model):

    project = models.ForeignKey(Project, blank=True, null=True)
    key = models.CharField(max_length=20)
    invoice_number = models.IntegerField()
    created_on = models.DateTimeField(auto_now_add=True, null=True)

    #still a draft when sent 0 times, and >= 2 are reminders
    num_times_sent = models.IntegerField(default=0)

    #timestamp of when we first asked for payment
    originally_sent_on = models.DateTimeField(blank=True, null=True)

    #timestamp of when we most recently asked for payment
    last_sent_on = models.DateTimeField(blank=True, null=True)

    #whether or not client has paid this invoice
    is_paid = models.BooleanField(default=False)

    #only one Invoice is the default
    is_default = models.BooleanField(default=False)

    please_use_static_function___Invoice_create___instead_of_building_by_hand = models.CharField(max_length=10)
    

    def __unicode__(self):

        if not self.project:
            return "Default Invoice representing %s unassigned hours. Do not display to user or modify via admin. Created with syncdb from intial_data fixture." % round(self.hours(), 1)
        else:
            return "Invoice to %s for %s hours" % (self.project.name, round(self.hours(), 1))


    #factory method to create an invoice and assigns all new time
    #entries to this invoice. it also bumps up the invoice #
    #and gives it a random key for its url
    def create_invoice(project):

        #create the invoice with a random key and incremented invoice #
        new_invoice = Invoice(project=project,
                key = rand_key(),
                invoice_number=Invoice.objects.all().count() + 1,
                please_use_static_function___Invoice_create___instead_of_building_by_hand="okay")
        new_invoice.save()

        #claim all time chunks without an invoice
        unclaimed_entries = TimeEntry.objects.filter(project=project,
                invoice__pk=1)
        for entry in unclaimed_entries:
            entry.invoice = new_invoice
            entry.save()

        return new_invoice
    
    #static factory constructor 
    create = staticmethod(create_invoice)


    def amount(self):
        if self.project:
            #standard case, when you've made an invoice for a particular
            #project
            return self.hours() * self.project.hourly_wage

        else:
            #case for the default invoice, which doesn't refer to a project
            #and shouldn't be viewed
            return 0


    def hours(self):

        #nonrel doesn't support aggregate(Sum(x)) so we find it by hand

        entries = TimeEntry.objects.filter(invoice=self)
        minutes = 0
        for entry in entries:
            minutes += entry.duration_in_minutes

        return minutes / 60.0


admin.site.register(Invoice)
admin.site.register(TimeEntry)
