from django.http import HttpResponse

from d_cards.models import Card



def reset_card_images(request):

    if not request.user.is_staff: 
        return HttpResponse("no permissions")

    for card in Card.objects.all():
        i = card.card_image(force_refresh=True)

    return HttpResponse("OK")






