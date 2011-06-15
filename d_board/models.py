from django.db import models
from django.contrib import admin

class Node(models.Model):

    # self-referential to make a tree.
    # null parent means it's the root, where the player is damaged from
    parent = models.ForeignKey("Node", blank=True, null=True)

    # always non-negative, range from 0-2
    row = models.IntegerField(default=0)

    # positive or negative from +-2
    x = models.IntegerField(default = 0)


    def __unicode__(self):
        return "Node: row=%s, x=%s" % (self.row, self.x)


admin.site.register(Node)
