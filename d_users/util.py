import logging

from d_game.models import Match

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

