import logging

from django.conf import settings
from django.db.models import QuerySet
from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.views.generic import TemplateView
from committees.models import AssociationGroup
from core.status_collective import AdminStatusViewMixin

from gworkspace_integration.workspace import SquireGoogleWorkspaceManager, get_workspace_manager

logger = logging.getLogger(__name__)


class WorkspaceStatusView(TemplateView):
    """
    An overview of data synced with Google Workspace. Connects to its API to determine whether
    this information is up-to-date. Also allows forced updating such data.
    """

    template_name = "gworkspace_integration/admin_status/workspace.html"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._workspace_manager: SquireGoogleWorkspaceManager | None = get_workspace_manager()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # context |= {
        #     "workspace_users": [],
        #     "workspace_groups": [],
        # }
        if self._workspace_manager is None:
            context["error"] = "Google Workspace integration not configured."
            context["alert_type"] = "warning"
            return context

        context |= {
            "workspace_users": self._workspace_manager.users(),
            "workspace_groups": [],
        }

        return context


class WorkspaceTabbedStatusView(AdminStatusViewMixin, WorkspaceStatusView):
    """Variant of the Workspace status view to use in a tabbed ViewCollective"""
