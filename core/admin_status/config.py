from django.urls import path
from core.admin_status.views import LogFileView
from core.status_collective import AdminStatusBaseConfig


class LogConfig(AdminStatusBaseConfig):
    url_keyword = "logs"
    name = "Logs"
    icon_class = "fas fa-bug"
    url_name = "logs"
    order_value = 2  # Value determining the order of the tabs on the admin status page

    def get_urls(self):
        return [
            path("log", LogFileView.as_view(config=self), name="logs"),
        ]
