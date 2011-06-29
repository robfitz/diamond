from django.shortcuts import render_to_response

from d_game.models import Puzzle


def puzzle_navigator(request):

    puzzles = Puzzle.objects.all() 

    return render_to_response("menus/puzzles.html", locals())
