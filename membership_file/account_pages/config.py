from django.urls import path
from user_interaction.accountcollective import AccountBaseConfig
from .views import MembershipDataView, MembershipChangeView


class MembershipConfig(AccountBaseConfig):
    url_keyword = "membership"
    name = "Membership"
    icon_class = "fas fa-id-card"
    url_name = "membership:view"
    order_value = 20

    namespace = "membership"

    requires_membership = False

    def get_urls(self):
        """Builds a list of urls"""
        return [
            path("", MembershipDataView.as_view(config=self), name="view"),
            path("edit/", MembershipChangeView.as_view(config=self), name="edit"),
        ]
