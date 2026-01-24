import logging

from django.conf import settings
from django.db.models import QuerySet
from django.contrib import messages
from django.http import HttpRequest, HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.views.generic import TemplateView
from committees.email import SquireEmailManager
from committees.models import AssociationGroup
from core.status_collective import AdminStatusViewMixin

from gworkspace_integration.admin_status.proxy import MailingListProxy
from gworkspace_integration.api.formats.groups import WorkspaceGroup, WorkspaceGroupMember
from gworkspace_integration.api.formats.users import WorkspaceUser
from gworkspace_integration.workspace import (
    MemberWorkspaceUserMap,
    SquireGoogleWorkspaceManager,
    WorkspaceUserMemberMap,
    get_workspace_manager,
)
from gworkspace_integration.workspace_manager.groups import WorkspaceGroupMemberSync, WorkspaceGroupMemberSyncStatus
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

    def _calc_member_sync_errors(self, member: Member | None, user: WorkspaceUser | None) -> list[str]:
        """Determine whether the member is correctly synced to a Workspace user. Output consists of all sync errors."""
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

    def _setup_members(self, member_map: MemberWorkspaceUserMap):
        """
        Sets up tuples consisting of Squire member, Workspace user pairs with other relevant info.

        :return: tuples containing
        - Squire member
        - Workspace user corresponding to that member (if it exists)
        - List of sync errors
        """
        res: list[tuple[Member, WorkspaceUser | None, list[str]]] = []
        for member, user in member_map.items():
            res.append((member, user, self._calc_member_sync_errors(member, user)))
        return res

    def _setup_orphans(self, user_map: WorkspaceUserMemberMap):
        """TODO

        Sets up tuples consisting of invalid Squire member, Workspace user pairs with other relevant info.
        """
        res: list[tuple[Member | None, WorkspaceUser, list[str]]] = []
        for user, member in user_map.items():
            if member is None or not member.is_active:
                res.append((member, user, self._calc_member_sync_errors(member, user)))
        return res

    def _calc_group_sync_errors(
        self, committee: MailingListProxy, wgroup: WorkspaceGroup | None, members_sync: list[WorkspaceGroupMemberSync]
    ) -> list[str]:
        """Determine whether the committee is correctly synced to a Workspace group. Output consists of all sync errors."""
        if wgroup is None:
            return []

        res: list[str] = []
        if committee.name != wgroup.name:
            res.append("group_name")
        if committee.description != wgroup.description:
            res.append("group_description")
        if committee.email != wgroup.email:
            res.append("group_email")
        if any(x.status != WorkspaceGroupMemberSyncStatus.SYNC_UP_TO_DATE for x in members_sync):
            res.append("group_members")
        if any(x.status == WorkspaceGroupMemberSyncStatus.SYNC_INVALID for x in members_sync):
            res.append("group_members_invalid")
        return res

    def _get_mailinglist_data_for_view(
        self,
        committee: MailingListProxy,
        group: WorkspaceGroup | None,
        res: list[tuple[MailingListProxy, WorkspaceGroup | None, list[WorkspaceGroupMemberSync], list[str]]],
    ) -> None:
        """
        Gets the data to display a mailing list and its subscribers in this view. The result is appended to the resulting list `res`

        :param: res, tuples containing
        - Squire committee
        - Workspace group corresponding to that committee (if it exists)
        - The Workspace group members according to Squire, and their sync status to the Workspace group
        - List of sync errors
        """
        synced_group_members = []
        if group is not None:
            # Do not sync invalid committee members
            synced_group_members = self._workspace_manager.calc_sync_status_group_members(
                group, committee, is_allow_invalid=False
            )
        res.append(
            (
                committee,
                group,
                synced_group_members,
                self._calc_group_sync_errors(committee, group, synced_group_members) if group is not None else [],
            )
        )

    def _setup_groups(
        self, groups: list[WorkspaceGroup]
    ) -> list[tuple[MailingListProxy, WorkspaceGroup | None, list[WorkspaceGroupMemberSync], list[str]]]:
        """
        Sets up tuples consisting of Squire committee, Workspace group pairs with other relevant info.
        """
        assert self._workspace_manager is not None
        committees = self._workspace_manager.get_active_committees()
        res = []
        for committee in committees:
            committee = MailingListProxy.from_committee(committee)
            group = self._workspace_manager.get_group_for_committee(committee, groups)
            self._get_mailinglist_data_for_view(committee, group, res)

        return res

    def _setup_member_mailing_lists(
        self, groups: list[WorkspaceGroup]
    ) -> list[tuple[MailingListProxy, WorkspaceGroup | None, list[WorkspaceGroupMemberSync], list[str]]]:
        """
        Sets up tuples consisting of Squire member mailing lists, Workspace group pairs with other relevant info.
        """
        assert self._workspace_manager is not None
        mailing_lists = self._workspace_manager._email_mgr.settings.mailing_lists
        res = []
        for mailing_list in mailing_lists.items():
            committee = MailingListProxy.from_member_mailing_list(mailing_list)
            group = self._workspace_manager.get_group_for_mailinglist(mailing_list[0], groups)
            self._get_mailinglist_data_for_view(committee, group, res)
        return res

    def _setup_committee_mailing_lists(
        self, groups: list[WorkspaceGroup]
    ) -> list[tuple[MailingListProxy, WorkspaceGroup | None, list[WorkspaceGroupMemberSync], list[str]]]:
        """
        Sets up tuples consisting of Squire committee mailing lists, Workspace group pairs with other relevant info.
        """
        assert self._workspace_manager is not None
        res = []
        for email in self._workspace_manager._email_mgr.settings.committee_settings.global_addresses:
            committee = MailingListProxy.from_committee_mailing_list(email)
            group = self._workspace_manager.get_group_for_mailinglist(email, groups)
            self._get_mailinglist_data_for_view(committee, group, res)
        return res

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self._workspace_manager is None:
            context["error"] = "Google Workspace integration not configured."
            context["alert_type"] = "warning"
            return context
        users = self._workspace_manager.users()
        groups = self._workspace_manager.groups()

        member_map, user_map = self._workspace_manager.get_member_user_mappings()

        workspace_pairs = self._setup_members(member_map)
        orphan_pairs = self._setup_orphans(user_map)
        context |= {
            "domain": self._workspace_manager._client.domain,
            "workspace_domains": self._workspace_manager._client.workspace_domains,
            "workspace_pairs": workspace_pairs,
            "orphan_users": orphan_pairs,
            "workspace_groups": self._setup_groups(groups),
            "workspace_mailing_lists": self._setup_member_mailing_lists(groups),
            "workspace_committee_lists": self._setup_committee_mailing_lists(groups),
        }

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        if "sync_group_members" not in request.POST:
            messages.error(self.request, "Missing sync_group_members in post data")
            return HttpResponseBadRequest("Invalid POST data passed. Missing sync_group_members")
        mailinglist_type, pk = request.POST["sync_group_members"].split("-", 1)

        committee: MailingListProxy = None
        group: WorkspaceGroup = None
        if mailinglist_type == "committee":
            try:
                committee = MailingListProxy.from_committee(AssociationGroup.objects.get(pk=pk))
                group = self._workspace_manager.get_group_for_committee(committee)
            except AssociationGroup.DoesNotExist:
                return HttpResponseBadRequest(
                    f"Attempted to update Workspace group members for committee_id {pk}. Such committee does not exist!"
                )
        elif mailinglist_type == "memberalias":
            try:
                mailing_list = next(
                    (email, settings)
                    for email, settings in self._workspace_manager._email_mgr.settings.mailing_lists.items()
                    if SquireEmailManager.mailing_list_to_id(email) == pk
                )
                pk = mailing_list[0]
                committee = MailingListProxy.from_member_mailing_list(mailing_list)
                group = self._workspace_manager.get_group_for_mailinglist(mailing_list[0])
            except StopIteration:
                return HttpResponseBadRequest(
                    f"Attempted to update Workspace group members for member alias {pk}. Such alias does not exist!"
                )
        else:
            err = f"Unknown group type {mailinglist_type} (id {pk}). Could not sync!"
            messages.error(err)
            return HttpResponseBadRequest(err)

        self._workspace_manager.logger.info(
            f"{request.user.username} ({request.user.id}) force synced group members for committee {committee.name} ({pk})"
        )
        self._workspace_manager.bulk_sync_group_members(committee, group)
        messages.success(self.request, f"Updated group members for {committee.name} ({pk}).")
        return HttpResponseRedirect(request.get_full_path())


class WorkspaceTabbedStatusView(AdminStatusViewMixin, WorkspaceStatusView):
    """Variant of the Workspace status view to use in a tabbed ViewCollective"""
