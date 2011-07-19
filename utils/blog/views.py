import logging

from django.template.defaultfilters import slugify
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.core import serializers

from utils.blog.models import Post

def show_post(request, slug):

    post = None 

    for p in Post.objects.all():
        if slugify(p.title) == slug: 
            post = p 
            break

    if not post:
        return HttpResponseRedirect('/blog/')

    posts = [post] 
    return render_to_response('utils/blog/blog.html', locals())
            

def blog(request):

    if request.user.is_staff:
        posts = Post.objects.all().order_by("-pk")[:5]
    else:
        posts = Post.objects.filter(is_draft=False).order_by("-pk")[:5] 

    return render_to_response('utils/blog/blog.html', locals())


def recent_posts(request):

    posts = Post.objects.filter(is_draft=False).order_by("-pk")[:5] 

    json = serializers.serialize("json", posts) 
    return HttpResponse(json, "application/javascript")
