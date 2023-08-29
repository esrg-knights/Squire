from django.urls import path

from core.status_collective import AdminStatusBaseConfig
from mailcow_integration.admin_status.views import MailcowTabbedStatusView


class MailcowStatusConfig(AdminStatusBaseConfig):
    url_keyword = "mailcow"
    name = "Mailcow"
    icon_class = "far fa-envelope"
    url_name = "mailcow_status"
    order_value = 1  # Value determining the order of the tabs on the admin status page

    def get_urls(self):
        return [
            path("", MailcowTabbedStatusView.as_view(config=self), name="mailcow_status"),
        ]
