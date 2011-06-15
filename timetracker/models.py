from django.db import models
from django.contrib import admin


class Client(models.Model):
    
    company_name = models.CharField(max_length="50")
    contact_email = models.EmailField()
    contact_name = models.CharField(max_length="50", blank=True, default="")
    
    address_1 = models.CharField(max_length="50", blank=True, default="")
    address_2 = models.CharField(max_length="50", blank=True, default="")
    address_3 = models.CharField(max_length="50", blank=True, default="")
    address_4 = models.CharField(max_length="50", blank=True, default="")


    def __unicode__(self):
        return self.company_name


class Project(models.Model):

    name = models.CharField(max_length="20")
    hourly_wage = models.IntegerField(default="50")
    currency = models.CharField(max_length="3", default="GBP")

    client = models.ForeignKey(Client, null=True, blank=True)


    def __unicode__(self):
        return self.name


    def unpaid_hours(self):
        entries = self.timeentry_set.filter(invoice__isnull=True)
        entries = self.timeentry_set.filter(invoice=1)

        minutes = 0
        for entry in entries:
            minutes += entry.duration_in_minutes

        return minutes / 60.0


    def unpaid_amount(self):
        return self.unpaid_hours() * self.hourly_wage




admin.site.register(Client)
admin.site.register(Project)
