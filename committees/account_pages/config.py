from django.urls import path

from user_interaction.config import AccountConfig

from .views import AssociationGroupAccountView



class TestAccountConfig(AccountConfig):
    url_keyword = 'my_groups'
    tab_select_keyword = 'tab_association_groups'
    name = 'My groups'
    url_name = 'account_group'

    def get_urls(self):
        """ Builds a list of urls """
        return [
            path('', AssociationGroupAccountView.as_view(), name='account_group'),
        ]