from django.conf.urls.defaults import *

urlpatterns = patterns('', 
        (r'^$', 'utils.blog.views.blog'),
        (r'^recent/$', 'utils.blog.views.recent_posts'),
        (r'^(?P<slug>[^/]+)/$', 'utils.blog.views.show_post'),

    )
