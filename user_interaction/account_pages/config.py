from django.urls import path

from user_interaction.config import AccountConfig

from .views import SiteAccountView


class TestAccountConfig(AccountConfig):
    url_keyword = 'site'
    tab_select_keyword = 'tab_member_info'
    name = 'Account'
    url_name = 'site_account'

    def get_urls(self):
        """ Builds a list of urls """
        return [
            path('', SiteAccountView.as_view(), name='site_account'),
        ]
