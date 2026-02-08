from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum

from gworkspace_integration.api.client import GoogleWorkspaceSettings
from gworkspace_integration.api.formats.groups import WorkspaceGroupMember
from gworkspace_integration.workspace_manager.planner.proxy import WorkspaceGroupMemberProxy


class WorkspaceGroupMemberSyncStatus(Enum):
    """What needs to happen to a Workspace Group Member in order for it to be synced with Squire"""

    SYNC_NOTOUCH = 0  # Manual override; not managed by Squire
    SYNC_SHOULD_UPDATE = 1
    SYNC_SHOULD_ADD = 2
    SYNC_SHOULD_REMOVE = 3
    SYNC_INVALID = 4
    SYNC_UP_TO_DATE = 5


@dataclass(eq=False)
class WorkspaceGroupMemberSync:
    """Sync status for a workspace group member in a Squire committee"""

    wgroup_member: WorkspaceGroupMember
    status: WorkspaceGroupMemberSyncStatus = WorkspaceGroupMemberSyncStatus.SYNC_UP_TO_DATE
    wmember_proxy: WorkspaceGroupMemberProxy | None = None
    sqmember_proxy: WorkspaceGroupMemberProxy | None = None

    @property
    def name(self):
        if self.sqmember_proxy:
            return self.sqmember_proxy.name
        if self.wmember_proxy:
            return self.wmember_proxy.name
        return "<Invalid Group Member>"


class SquireWorkspaceGroupSyncHelper:
    """Helper class to calculate a 'diff' between to sets of members"""

    def __init__(self, settings: GoogleWorkspaceSettings):
        self.settings = settings

    def get_sync(
        self, desired_members: Iterable[tuple[WorkspaceGroupMember, WorkspaceGroupMemberProxy]]
    ) -> Iterator[WorkspaceGroupMemberSync]:
        """Sets up a sync for desired members, to be used by other methods in this class."""
        for wmember, member in desired_members:
            yield WorkspaceGroupMemberSync(wmember, WorkspaceGroupMemberSyncStatus.SYNC_UP_TO_DATE, None, member)

    def calc_base_sync(
        self,
        current_members: Iterable[WorkspaceGroupMember],
        desired_members_sync: Iterable[WorkspaceGroupMemberSync],
    ) -> Iterator[WorkspaceGroupMemberSync]:
        """
        Gets a "diff" of a given Workspace group, and how that group should be populated according to a committee.
        Sync statuses include:
        - up-to-date
        - additions (not present in the Workspace group, but should be due to the committee)
        - removals (present in the Workspace group, but shouldn't)
        - updates (e.g. in OWNER/MEMBER-roles)
        """
        current_wgroup_members = set(current_members)

        for desired_member_sync in desired_members_sync:
            # Match based on email; this is the unique identifier for a group member in Google Workspace
            # Workspace Users shouldn't directly be added to these groups; we wish to include the members' non-Workspace emails
            current_wgroup_member = next(
                filter(lambda m: m.email == desired_member_sync.wgroup_member.email, current_wgroup_members), None
            )

            if current_wgroup_member is None:
                # No corresponding workspace member found to a current committee member. It should be added!
                desired_member_sync.status = WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_ADD
                yield desired_member_sync
                continue

            # GroupMember was found. Remove it so we are left with the Workspace members that do not have a corresponding Squire member.
            current_wgroup_members.remove(current_wgroup_member)
            # Update group member ID based on what we already retrieved from GWorkspace
            desired_member_sync.wgroup_member.id = current_wgroup_member.id

            if (
                current_wgroup_member.role != desired_member_sync.wgroup_member.role
                or current_wgroup_member.type != desired_member_sync.wgroup_member.type
            ):
                # Info is out of date!
                desired_member_sync.status = WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_UPDATE
                yield desired_member_sync
                continue

            # up-to-date
            yield desired_member_sync

        # Should remove all remaining users that were in the group previously
        for unmatched_gmember in current_wgroup_members:
            # desired_members_sync.append(
            yield WorkspaceGroupMemberSync(unmatched_gmember, WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_REMOVE)

    def verify_sync(self, group_members_sync: list[WorkspaceGroupMemberSync]) -> Iterator[WorkspaceGroupMemberSync]:
        """
        Calc additional sync statuses
        - invalid (could not sync due to some restrictions)
        - no-touch (member was added manually in Google Workspace; don't touch these)
        """
        for sync in group_members_sync:
            # Update validity
            if sync.sqmember_proxy is not None and not sync.sqmember_proxy.is_valid(self.settings):
                sync.status = WorkspaceGroupMemberSyncStatus.SYNC_INVALID

            # Update manual additions (these aren't synced)
            if sync.wmember_proxy is not None and sync.wmember_proxy.is_manual(self.settings):
                sync.status = WorkspaceGroupMemberSyncStatus.SYNC_NOTOUCH

            yield sync
