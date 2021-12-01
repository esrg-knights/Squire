from django.urls import path

from user_interaction.config import AccountConfig

from .views import SiteAccountView, AccountPasswordChangeView, AccountLayoutPreferencesUpdateView


class TestAccountConfig(AccountConfig):
    url_keyword = 'site'
    tab_select_keyword = 'tab_account_info'
    name = 'Account'
    url_name = 'site_account'

    def get_urls(self):
        """ Builds a list of urls """
        return [
            path('', SiteAccountView.as_view(), name='site_account'),
            path('change-password/', AccountPasswordChangeView.as_view(), name='password_change'),
            path('change-layout/', AccountLayoutPreferencesUpdateView.as_view(), name='layout_change'),
        ]
