from django.urls import path

from user_interaction.accountcollective import AccountBaseConfig

from .views import *

# TODO: This config might fit better on one of the already existing account subpages
#   It's only available to members.
class MailSettingsConfig(AccountBaseConfig):
    url_keyword = 'email'
    name = 'Email'
    icon_class = 'far fa-envelope'
    url_name = 'email_preferences'
    order_value = 11  # Value determining the order of the tabs on the Account page

    def get_urls(self):
        """ Builds a list of urls """
        return [
            path('', EmailPreferencesChangeView.as_view(config=self), name='email_preferences'),
        ]
