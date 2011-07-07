def get_deck_from(request):

    deck = None

    if request.user.is_authenticated():
        # already logged in, should have a deck
        try:
            profile = request.user.get_profile() 
        except:
            # if they account was created outside the normal
            # signup process and doesn' thave a profile and
            # default deck, get them started
            d_users.models.create_user_profile(d_users.models.User, request.user, True)
            profile = request.user.get_profile() 

        # new profiles come w/ a default deck, while existing
        # profiles have their changes and whatnot saved there
        deck = profile.deck
    else:
        # not logged in 
        try:
            # get my custom deck progress that i built 
            # via the editor (during this session)
            deck_id = request.session.get("deck_id")
            deck = Deck.objects.get(id=deck_id)
        except:
            # start me a new deck if i haven't already
            # worked on one this session
            deck = Deck.create_starting_deck()
            deck.save()
            request.session["deck_id"] = deck.id

    return deck

