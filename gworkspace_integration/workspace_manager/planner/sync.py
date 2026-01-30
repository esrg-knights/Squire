from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from gworkspace_integration.api.client import GoogleWorkspaceSettings
from gworkspace_integration.api.formats.groups import WorkspaceGroupMember
from gworkspace_integration.api.formats.users import WorkspaceUser
from gworkspace_integration.workspace_manager.planner.proxy import MailingListMemberProxy


class WorkspaceGroupMemberSyncStatus(Enum):
    """What needs to happen to a Workspace Group Member in order for it to be synced with Squire"""

    SYNC_UP_TO_DATE = 0
    SYNC_SHOULD_UPDATE = 1
    SYNC_SHOULD_ADD = 2
    SYNC_SHOULD_REMOVE = 3
    SYNC_INVALID = 4


@dataclass(eq=False)
class WorkspaceGroupMemberSync:
    """Sync status for a workspace group member in a Squire committee"""

    wgroup_member: WorkspaceGroupMember
    status: WorkspaceGroupMemberSyncStatus = WorkspaceGroupMemberSyncStatus.SYNC_UP_TO_DATE
    workspace_user: WorkspaceUser | None = None
    squire_member: MailingListMemberProxy | None = None

    @property
    def name(self):
        if self.squire_member:
            return self.squire_member.name
        if self.workspace_user:
            return self.workspace_user.name.fullName
        return ""


class SquireWorkspaceGroupPlanner:
    """Helper class to calculate a 'diff' between to sets of members"""

    def __init__(self, settings: GoogleWorkspaceSettings):
        self.settings = settings

    def is_email_valid_for_sync(self, email: str) -> bool:
        """Whether a Workspace group member can be synced"""
        if email == self.settings.directory_admin_username:
            return True

        return not email.endswith(self.settings.primary_domain) and not any(
            email.endswith(domain) for domain in self.settings.domains
        )

    def calc_sync_status_group_members(
        self,
        current_members: Iterable[WorkspaceGroupMember],
        desired_members: Iterable[tuple[WorkspaceGroupMember, MailingListMemberProxy]],
        is_allow_invalid=False,
    ) -> list[WorkspaceGroupMemberSync]:
        """
        Gets a "diff" of a given Workspace group, and how that group should be populated according to a committee.
        Sync statuses include up-to-date, additions (not present in the Workspace group, but should be due to the
        committee), removals (present in the Workspace group, but shouldn't), and updates (e.g. in OWNER/MEMBER-roles)
        """

        # current_workspace_members = set(self.group_members(group))
        current_wgroup_members = set(current_members)
        # committee_members_sync = self._get_group_members_sync_for_committee(committee)
        committee_members_sync = [
            WorkspaceGroupMemberSync(wmember, WorkspaceGroupMemberSyncStatus.SYNC_UP_TO_DATE, None, member)
            for wmember, member in desired_members
        ]

        for cmember_sync in committee_members_sync:
            # Match based on email; this is the unique identifier for a group member in Google Workspace
            # Workspace Users shouldn't directly be added to these groups; we wish to include the members' non-Workspace emails
            current_wgroup_member = next(
                filter(lambda m: m.email == cmember_sync.wgroup_member.email, current_wgroup_members), None
            )

            if current_wgroup_member is None:
                # No corresponding workspace member found to a current committee member. It should be added!
                cmember_sync.status = WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_ADD
                continue

            # GroupMember was found. Remove it so we are left with the Workspace members that do not have a corresponding Squire member.
            current_wgroup_members.remove(current_wgroup_member)

            if (
                current_wgroup_member.role != cmember_sync.wgroup_member.role
                or current_wgroup_member.type != cmember_sync.wgroup_member.type
            ):
                # Info is out of date!
                cmember_sync.status = WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_UPDATE
                if not cmember_sync.wgroup_member.id:
                    cmember_sync.wgroup_member.id = current_wgroup_member.id
                continue

        # All unmatched group members should be removed
        for gmember_to_remove in current_wgroup_members:
            committee_members_sync.append(
                WorkspaceGroupMemberSync(
                    gmember_to_remove,
                    WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_REMOVE,
                    # workspace_user=self.get_user_by_id(gmember_to_remove.id),
                )
            )

        if not is_allow_invalid:
            for sync in committee_members_sync:
                if not self.is_email_valid_for_sync(sync.wgroup_member.email):
                    sync.status = WorkspaceGroupMemberSyncStatus.SYNC_INVALID

        return committee_members_sync
