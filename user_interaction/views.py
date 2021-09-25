from datetime import timedelta
from django.utils import timezone
from django.views.generic import TemplateView
from django.views.decorators.http import require_safe


from activity_calendar.models import ActivityMoment, Activity
from core.forms import LoginForm



def home_screen(request, *args, **kwargs):
    if request.user.is_authenticated:
        return HomeUsersView.as_view()(request)
    else:
        return HomeNonAuthenticatedView.as_view()(request)


class HomeNonAuthenticatedView(TemplateView):
    template_name = "user_interaction/home_non_authenticated.html"

    def get_context_data(self, **kwargs):
        return super(HomeNonAuthenticatedView, self).get_context_data(
            form=LoginForm(),
            **kwargs
        )

class HomeUsersView(TemplateView):
    template_name = "user_interaction/home_users.html"

    def get_context_data(self, **kwargs):
        # Get a list of all upcoming activities
        start_date = timezone.now()
        end_date = start_date + timedelta(days=7)

        activities = []
        for activity in Activity.objects.filter(published_date__lte=timezone.now()):
            for activity_moment in activity.get_activitymoments_between(start_date, end_date):
                activities.append(activity_moment)


        kwargs.update(
            activities=sorted(activities, key=lambda activity: activity.start_date)
        )

        return super(HomeUsersView, self).get_context_data(**kwargs)
