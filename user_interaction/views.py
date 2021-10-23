from datetime import timedelta
import random

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import FormView
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from dynamic_preferences.users.forms import user_preference_form_builder

from activity_calendar.models import Activity
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


welcome_messages = [
    "Do not be alarmed by the Dragons. They're friendly :)",
    "Have you been triumphant today or do you want to borrow a sword?",
    "Friendly reminder that we are not a cult!",
    "This line has been occupied by the shadow board.",
    "Today is a great day, cause you just lost the game",
    "AP <you>: Make new greeting lines",
    "The app has improvd: now even mor guranteed to nor contain splelling errors!",
    "Time to join the dark knights side, we have cookies",
    "Message from the board: We are aware of the kobold infestation.",
    "I hope you are having a splendid day",
    "Knights room now open 23/7",
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Fusce tristique quam rutrum augue dapibus, quis condimentum ligula porttitor.",
    "Don't forget to like, subscribe, and hit that notification bell!"
    "",
    "Für Wissen... und Weisheit!",
    "Man, man, man. Wat een avontuur!",
    "This is what we will offer this time, now available in wonderous rhyme!",
    "Have an amazing quote said around the Knights? Email it to quotcie@kotkt.nl",
    "Ḛ͈̅͆̑͂͟ͅv̠͔̗͒͗͟ͅe͊͌ͣͫ҉͙͈͍̘̲r͖̖̼̐̏̍̕y̛͉͍̲̹͔̫̐ͅtͥͦ̎҉̪̰̪̭͖̮̰ͅh̛͇̮̝ͬ̓į̮̞̬̟̫̼̌ͭ̀n̉ͪ҉̬̭͈̫̱̣̳ͅg̤͕̲͚̓͢ ̝͚̙͚̱̬̎̈́͌͟ḯ̡̥̰̼͍͎ͪs̨̜̺̣͌̈́ͭ̚ ̛̞̖͉͈̖̓ͨ̇n̨̮̺͈̩͇̞͍̽́o̲͔̹̹̩̰̙͙̐͘r̟͍͚ͣͥ̂̈́͠m̷̻͎ͤ̅ͬa̜͓͎͇̭̖ͮ̓̎̃͘l̷̞̬̩̮̠̟̤̐͗ͪ",
    "ᗷᒪOOᗪ ᔕᗩᑕᖇᗩᖴIᑕEᔕ ᗩᖇE ᑎOT ᗩᒪᒪOᗯEᗪ Oᑎ TᕼE Tᑌ/E ᑕᗩᗰᑭᑌᔕ",
    "Good dawning to thee, friend. May thy day be blissful.",
]


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
            activities=sorted(activities, key=lambda activity: activity.start_date),
            greeting_line = random.choice(welcome_messages)
        )

        return super(HomeUsersView, self).get_context_data(**kwargs)


class UpdateUserPreferencesView(LoginRequiredMixin, FormView):
    """ View for updating user preferences """
    template_name = 'user_interaction/preferences_change_form.html'
    success_url = reverse_lazy('core:user_accounts/account')

    def get_form_class(self):
        return user_preference_form_builder(instance=self.request.user, section='layout')

    def form_valid(self, form):
        message = _("Your preferences have been updated!")
        messages.success(self.request, message)
        form.update_preferences()
        form = self.get_form()
        return super().form_valid(form)
