from django.urls import path

from user_interaction.accountcollective import AccountBaseConfig

from .views import AssociationGroupAccountView



class TestAccountConfig(AccountBaseConfig):
    url_keyword = 'my_groups'
    name = 'My groups'
    url_name = 'account_group'
    order_value = 30

    def get_urls(self):
        """ Builds a list of urls """
        return [
            path('', AssociationGroupAccountView.as_view(config=self), name='account_group'),
        ]
