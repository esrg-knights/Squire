from django.urls import path
from user_interaction.accountcollective import AccountBaseConfig
from .views import AchievementAccountView


class AchievementConfig(AccountBaseConfig):
    url_keyword = "achievements"
    name = "Achievements"
    icon_class = "fas fa-trophy"
    url_name = "achievements"
    order_value = 99

    def get_urls(self):
        """Builds a list of urls"""
        return [
            path("", AchievementAccountView.as_view(config=self), name="achievements"),
        ]
