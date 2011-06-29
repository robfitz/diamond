from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',

    ('^ah/warmup$', 'djangoappengine.views.warmup'),

    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),

    ('^deck/$', 'd_cards.views.edit_deck'),
    ('^deck/get_library_cards/$', 'd_cards.views.get_library_cards'),
    ('^deck/save/$', 'd_cards.views.save_deck'),

    ('^playing/first_turn/$', 'd_game.views.first_turn'),
    ('^playing/end_turn/$', 'd_game.views.end_turn'),
    ('^$', 'd_game.views.playing'),

    ('^puzzle/$', 'd_game.views.puzzle'),
    ('^puzzles/$', 'd_menus.views.puzzle_navigator'),

    #('', 'django.views.generic.simple.direct_to_template',
     #{'template': 'home.html'}),

    #static assets (should be local-only)                   
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': 'media'}),
)
