from django import template

from gworkspace_integration.workspace_manager.services.groups import (
    WorkspaceGroupMemberSync,
    WorkspaceGroupMemberSyncStatus,
)

register = template.Library()


@register.filter
def is_allow_sync_members(gmembers: list[WorkspaceGroupMemberSync]):
    return any(
        x.status not in (WorkspaceGroupMemberSyncStatus.SYNC_UP_TO_DATE, WorkspaceGroupMemberSyncStatus.SYNC_INVALID)
        for x in gmembers
    )
