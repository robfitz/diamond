from django.http import HttpResponse

from d_feedback.models import PuzzleFeedback, PuzzleFeedbackForm
from d_game.models import Match 


def puzzle_feedback(request): 

    if request.method == "POST": 

        match = Match.objects.get(id=request.session["match"])

        feedback = PuzzleFeedback(match=match,
                puzzle=match.puzzle)
        form = PuzzleFeedbackForm(request.POST, instance=feedback) 
        feedback = form.save(commit=False)


        # save feedback iff it's non-trivial
        if feedback.feedback and feedback.difficulty != "no opinion": 
            # feedback.save()
            form.save() 

    return HttpResponse("ok")

