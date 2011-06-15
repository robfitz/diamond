from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',

    ('^ah/warmup$', 'djangoappengine.views.warmup'),

    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),


    ('playing/draw/', 'd_game.views.draw'),
    ('', 'd_game.views.playing'),

    ('', 'django.views.generic.simple.direct_to_template',
     {'template': 'home.html'}),

    #static assets (should be local-only)                   
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': 'media'}),
)
