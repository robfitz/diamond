from django.db import models 
from django.contrib import admin


class Post(models.Model):

    title = models.CharField(max_length=140)
    body = models.TextField()
    thumbnail = models.URLField(blank=True, default="")

    timestamp = models.DateTimeField(auto_now_add=True) 
    is_draft = models.BooleanField(default=False) 


    def to_js(self):

        js = """$("<div class='blog_teaser'><img src="%s" /><h4>%s</h4>%s""" % (self.thumbnail, self.title, self.body)

        return js 


admin.site.register(Post)
