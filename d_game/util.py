import datetime

from django.utils.functional import wraps
from d_metrics.models import UserMetrics


def daily_activity(view):

    @wraps(view)

    def inner(request, *args, **kwargs):

        if request.user.is_authenticated(): 
            # logged in user should already have metrics
            # metrics = UserMetrics.objects.get(user=user)
            metrics = request.user.metrics

        else:
            try:
                metrics = UserMetrics.objects.get(anon_session_key=request.session.session_key)
            except:
                metrics = UserMetrics(anon_session_key=request.session.session_key,
                        first_visit_version=0,
                        signup_version=0)
                metrics.save()

        if len(metrics.login_dates) == 0 or metrics.login_dates[-1] != datetime.date.today():
            # if we haven't already marked the user
            # as active for today, do so now!
            
            metrics.login_dates.append(datetime.date.today())
            metrics.save()

        # call the wrapped view
        return view(request, *args, **kwargs)

    # return the wrapped function, replacing
    # the original view
    return inner 
