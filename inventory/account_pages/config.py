from django.urls import path, include

from user_interaction.accountcollective import AccountBaseConfig

from .views import *


class AccountInventoryConfig(AccountBaseConfig):
    url_keyword = "inventory"
    name = "Inventory"
    icon_class = "fas fa-archive"
    url_name = "inventory:member_items"
    order_value = 70

    namespace = "inventory"

    def get_urls(self):
        """Builds a list of urls"""
        return [
            path("", MemberItemsOverview.as_view(config=self), name="member_items"),
            path(
                "<int:ownership_id>/",
                include(
                    [
                        path("take_home/", MemberItemRemovalFormView.as_view(config=self), name="member_take_home"),
                        path("give_out/", MemberItemLoanFormView.as_view(config=self), name="member_loan_out"),
                        path("edit_note/", MemberOwnershipAlterView.as_view(config=self), name="owner_link_edit"),
                    ]
                ),
            ),
        ]
