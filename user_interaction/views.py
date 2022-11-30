from datetime import timedelta
import random
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.utils import timezone

from dynamic_preferences.registries import global_preferences_registry

from activity_calendar.models import Activity
from core.forms import LoginForm
from membership_file.models import Membership
from utils.spoofs import optimise_naming_scheme


global_preferences = global_preferences_registry.manager()


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

################
# BEGIN APRIL 2022
################
class SquirePremiumView(TemplateView):
    template_name = "user_interaction/april_2022.html"
################
# END APRIL 2022
################

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

        welcome_name = self.request.member.first_name if self.request.member else self.request.user.first_name
        if global_preferences['homepage__april_2022']:
            # This bit is from the april fools joke 2022
            welcome_name = optimise_naming_scheme(welcome_name)

        activities = []
        for activity in Activity.objects.filter(published_date__lte=timezone.now(), is_public=True):
            for activity_moment in activity.get_activitymoments_between(start_date, end_date):
                activities.append(activity_moment)

        kwargs.update(
            activities=sorted(activities, key=lambda activity: activity.start_date),
            greeting_line = random.choice(welcome_messages),
            unique_messages = self.get_unique_messages(),
            welcome_name=welcome_name,
        )

        return super(HomeUsersView, self).get_context_data(**kwargs)

    def get_unique_messages(self):
        unique_messages = []

        if global_preferences['homepage__home_page_message']:
            unique_messages.append({
                'msg_text': str(global_preferences['homepage__home_page_message']),
                'msg_type': "info",
            })
        if global_preferences['membership__signup_year']:
            year = global_preferences['membership__signup_year']
            if not Membership.objects.filter(member=self.request.member, year=year).exists():
                unique_messages.append({
                    'msg_text': f"A new adventure awaits! Continue your membership into {year} now!",
                    'msg_type': "info",
                    'btn_text': "Continue Questing!",
                    'btn_url': reverse_lazy('membership_file/continue_membership'),
                })

        ################
        # BEGIN APRIL 2022
        ################
        # Squire Premium
        if global_preferences['homepage__april_2022']:
            unique_messages.append({
                'msg_text': "Squire 2.0 will release soon. Read about the details and new features it brings, and upgrade now!",
                'msg_type': "danger",
                'btn_text': "Visit Upgrade Page",
                'btn_url': reverse_lazy('user_interaction:squire_premium'),
            })
        ################
        # BEGIN APRIL 2022
        ################

        return unique_messages
