from django.urls import path
from user_interaction.config import AccountConfig
from .views import MembershipDataView, MembershipChangeView


class MembershipConfig(AccountConfig):
    url_keyword = 'membership'
    tab_select_keyword = 'tab_membership'
    name = 'Membership'
    url_name = 'membership:view'

    namespace = 'membership'

    def get_urls(self):
        """ Builds a list of urls """
        return [
            path('', MembershipDataView.as_view(), name='view'),
            path('edit/', MembershipChangeView.as_view(), name='edit'),
        ]
