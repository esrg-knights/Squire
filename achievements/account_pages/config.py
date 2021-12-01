from django.urls import path
from user_interaction.config import AccountConfig
from .views import AchievementAccountView


class AchievementConfig(AccountConfig):
    url_keyword = 'achievements'
    tab_select_keyword = 'tab_achievements'
    name = 'My achievements'
    url_name = 'achievements'

    def get_urls(self):
        """ Builds a list of urls """
        return [
            path('', AchievementAccountView.as_view(config=self), name='achievements'),
        ]
