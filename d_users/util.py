import logging

from d_game.models import Match, Puzzle


def has_permissions_for(puzzle, user, session_key):

    beaten_puzzle_ids = unique_puzzles_won(user, session_key)

    puzzles = Puzzle.objects.filter(state="approved") 

    # flag for unlocking only the first puzzle they haven't yet beaten
    unlock_next_unbeaten = True

    # we've already beaten that one, so it's unlocked
    # for sure
    if puzzle.id in beaten_puzzle_ids:
        return True

    # if we haven't yet beaten it, check if it's next
    # in line to be played
    for p in puzzles:
        if p.id in beaten_puzzle_ids:
            
            # if they've beaten a level, unlock the first
            # locked one after that. this means that if
            # we insert new levels after they've already
            # passed that point, they'll be able to either
            # go back to the new ones or pick up from
            # where they left off at the later levels.
            unlock_next_unbeaten = True

        else:
            if unlock_next_unbeaten:
                if p == puzzle:
                    return True
                unlock_next_unbeaten = False

    return False


def unique_puzzles_won(user, session_key):

    beaten_puzzle_ids = []

    try:
        profile = user.get_profile()
        beaten_puzzle_ids = profile.beaten_puzzle_ids

    except:
        # probably an anonymous user, so no profile
        beaten_matches = Match.objects.filter(session_key=session_key)
        for match in beaten_matches:
            if match.type == "puzzle" and match.winner == "friendly" and match.puzzle.id not in beaten_puzzle_ids:
                beaten_puzzle_ids.append(match.puzzle.id)

    return beaten_puzzle_ids

