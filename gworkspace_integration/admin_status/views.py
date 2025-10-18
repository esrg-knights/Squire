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

from gworkspace_integration.api.formats.users import WorkspaceUser
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

    def _validate(self, member: Member | None, user: WorkspaceUser | None) -> list[str]:
        """Validates a member with corresponding user data"""
        errors = []

        # Workspace active?
        if user is not None:
            user_member_id = next((eid.value for eid in user.external_ids if eid.type == "organization"), None)
            if user.deletionTime is not None:
                errors.append("deleted")
            if user.suspended:
                errors.append("suspended")
            if user.archived:
                errors.append("archived")

            if member is not None:
                # Assume the member and user refer to the same person
                assert (
                    str(member.pk) == user_member_id
                ), f"MemberID {member.pk} not present in user externalIds: {user.external_ids}"
                # Validate name
                if member.first_name != user.name.givenName:
                    errors.append("first_name")
                last_name = member.last_name
                if member.tussenvoegsel:
                    last_name = member.tussenvoegsel + " " + last_name
                if last_name != user.name.familyName:
                    errors.append("last_name")
                if member.email != user.recoveryEmail:
                    errors.append("recovery_email")
            else:
                errors.append("invalid_userid")

        if member is not None:
            if not member.is_active:
                errors.append("inactive")
        return errors

    def _setup_members(self, users: list[WorkspaceUser]) -> list[tuple[Member, WorkspaceUser | None, list[str]]]:
        """TODO"""
        assert self._workspace_manager is not None
        members = Member.objects.filter_active().order_by("first_name", "last_name")
        res: list[tuple[Member, WorkspaceUser | None, list[str]]] = []
        for member in members:
            user = self._workspace_manager.get_user_for_member(member, users)
            res.append((member, user, self._validate(member, user)))
        return res

    def _setup_orphans(self, users: list[WorkspaceUser]) -> list[tuple[Member | None, WorkspaceUser, list[str]]]:
        """TODO"""
        assert self._workspace_manager is not None
        res: list[tuple[Member | None, WorkspaceUser, list[str]]] = []
        for user in users:
            member = self._workspace_manager.get_member_for_user(user)
            if member is None or not member.is_active:
                res.append((member, user, self._validate(member, user)))
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
            "orphan_users": self._setup_orphans(users),
            "workspace_groups": [],
        }

        return context


class WorkspaceTabbedStatusView(AdminStatusViewMixin, WorkspaceStatusView):
    """Variant of the Workspace status view to use in a tabbed ViewCollective"""
