from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',

    ('^ah/warmup$', 'djangoappengine.views.warmup'),

    ('^$', 'django.views.generic.simple.direct_to_template', {'template': 'index.html'}),

    (r'^blog/', include('utils.blog.urls')),

    (r'^log/$', 'd_game.views.log'),
    (r'^log/(?P<match_id>.*)/$', 'd_game.views.log'),

    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    (r'^accounts/logout/$', 
        'django.contrib.auth.views.logout',
        { 'next_page': '/' }),
    (r'^accounts/register/$', 'd_users.views.register'),

    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/metrics/', 'd_metrics.views.user_metrics'),
    (r'^admin/', include(admin.site.urls)),

    (r'^edit_puzzle/$', 'd_editor.views.edit_puzzle'),
    (r'^edit_puzzle/setup/$', 'd_editor.views.get_puzzle_data'),

    ('^deck/$', 'd_editor.views.edit_deck'),
    ('^deck/get_library_cards_by_category/$', 'd_cards.views.get_library_cards'),
    ('^deck/save/$', 'd_cards.views.save_deck'),

    ('^playing/first_turn/$', 'd_game.views.first_turn'),
    ('^playing/end_turn/$', 'd_game.views.end_turn'),
    ('^play/$', 'd_game.views.playing'),

    ('^puzzle/$', 'd_game.views.puzzle'),
    ('^puzzles/$', 'd_menus.views.puzzle_navigator'),

    # submit mini-survey
    ('^feedback/puzzle/$', 'd_feedback.views.puzzle_feedback'),

    ('^no_ie/$', 'django.views.generic.simple.direct_to_template', {'template': 'misc/no_ie.html'}),

    ('^$', 'd_menus.views.puzzle_navigator'),
        

    #('', 'django.views.generic.simple.direct_to_template',
     #{'template': 'home.html'}),

    #static assets (should be local-only)                   
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': 'media'}),
)
