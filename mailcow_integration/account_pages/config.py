from typing import Optional
from django.apps import apps
from django.urls import path
from mailcow_integration.squire_mailcow import get_mailcow_manager

from user_interaction.accountcollective import AccountBaseConfig

from .views import TabbedEmailPreferencesChangeView


# TODO: This config might fit better on one of the already existing account subpages
#   It's only available to members.
class MailSettingsConfig(AccountBaseConfig):
    url_keyword = "email"
    name = "Email"
    icon_class = "far fa-envelope"
    url_name = "email_preferences"
    order_value = 11  # Value determining the order of the tabs on the Account page

    def is_enabled(self):
        # Can only update mail preferences if a Mailcow client is set up
        return get_mailcow_manager() is not None

    def get_urls(self):
        return [
            path("", TabbedEmailPreferencesChangeView.as_view(config=self), name="email_preferences"),
        ]
