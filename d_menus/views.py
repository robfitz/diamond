import logging

from django.shortcuts import render_to_response

from d_game.models import Puzzle, Match


def puzzle_navigator(request):

    logging.info("XXX sess %s: %s" % (request.session.session_key, request.session.get("beaten_puzzle_ids")))

    beaten_puzzle_ids = []
    try:
        profile = request.user.get_profile()
        beaten_puzzle_ids = profile.beaten_puzzle_ids
    except:
        # probably an anonymous user, so no profile
        beaten_matches = Match.objects.filter(session_key=request.session.session_key)
        for match in beaten_matches:
            if match.type == "puzzle" and match.puzzle.id not in beaten_puzzle_ids:
                beaten_puzzle_ids.append(match.puzzle.id)

    puzzles = Puzzle.objects.all() 

    # flag for unlocking only the first puzzle they haven't yet beaten
    unlock_next_unbeaten = True

    for puzzle in puzzles:
        if puzzle.id in beaten_puzzle_ids:
            puzzle.player_state = 'beaten' 
            # if they've beaten a level, unlock the first
            # locked one after that. this means that if
            # we insert new levels after they've already
            # passed that point, they'll be able to either
            # go back to the new ones or pick up from
            # where they left off at the later levels.
            unlock_next_unbeaten = True

        else:
            if unlock_next_unbeaten:
                puzzle.player_state = 'current'
                # only unlock the first in a series
                # of unbeaten levels
                unlock_next_unbeaten = False
            else:
                puzzle.player_state = 'locked'


    return render_to_response("menus/puzzles.html", locals())
