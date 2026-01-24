from dataclasses import dataclass
from enum import Enum

from gworkspace_integration.admin_status.proxy import MailingListMemberProxy
from gworkspace_integration.api.formats.groups import WorkspaceGroupMember
from gworkspace_integration.api.formats.users import WorkspaceUser
from membership_file.models import Member


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
    workspace_user: WorkspaceUser = None
    squire_member: MailingListMemberProxy = None
