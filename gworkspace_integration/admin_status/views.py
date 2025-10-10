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

from gworkspace_integration.api.formats import WorkspaceUser
from gworkspace_integration.workspace import SquireGoogleWorkspaceManager, get_workspace_manager
from membership_file.models import Member

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

    def _setup_members(self, users: list[WorkspaceUser]):
        """TODO"""
        assert self._workspace_manager is not None
        members = Member.objects.filter_active().order_by("first_name", "last_name")
        res: list[tuple[Member, WorkspaceUser | None]] = []
        for member in members:
            res.append((member, self._workspace_manager.get_user_for_member(member)))
        return res

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self._workspace_manager is None:
            context["error"] = "Google Workspace integration not configured."
            context["alert_type"] = "warning"
            return context
        users = self._workspace_manager.users()
        context |= {
            "domain": self._workspace_manager._client._domain,
            "workspace_pairs": self._setup_members(users),
            "workspace_groups": [],
        }

        return context


class WorkspaceTabbedStatusView(AdminStatusViewMixin, WorkspaceStatusView):
    """Variant of the Workspace status view to use in a tabbed ViewCollective"""
