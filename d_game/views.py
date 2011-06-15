from django.shortcuts import render_to_response

from d_board.models import Node

def playing(request):

    board = Node.objects.all()

    return render_to_response("playing.html", locals())
    

