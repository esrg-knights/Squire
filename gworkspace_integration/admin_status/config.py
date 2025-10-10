from django.urls import path

from core.status_collective import AdminStatusBaseConfig
from gworkspace_integration.admin_status.views import WorkspaceTabbedStatusView


class GoogleWorkspaceStatusConfig(AdminStatusBaseConfig):
    url_keyword = "workspace"
    name = "Google Workspace"
    icon_class = "fab fa-google"
    url_name = "workspace_status"
    order_value = 1  # Value determining the order of the tabs on the admin status page

    def get_urls(self):
        return [
            path("", WorkspaceTabbedStatusView.as_view(config=self), name="workspace_status"),
        ]
