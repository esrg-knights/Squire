from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum
import re
from typing import Generator

from committees.models import AssociationGroup
from gworkspace_integration.api.client import GoogleWorkspaceSettings
from gworkspace_integration.api.services.directory_service import DirectoryService
from gworkspace_integration.workspace_manager.planner.proxy import MailingListMemberProxy, MailingListProxy
from gworkspace_integration.api.formats.groups import (
    WorkspaceGroup,
    WorkspaceGroupMember,
    WorkspaceGroupMemberDeliverySettings,
    WorkspaceGroupMemberRole,
    WorkspaceGroupMemberType,
)
from gworkspace_integration.api.formats.users import WorkspaceUser
from gworkspace_integration.workspace_manager.planner.sync import (
    SquireWorkspaceGroupPlanner,
    WorkspaceGroupMemberSync,
    WorkspaceGroupMemberSyncStatus,
)
from gworkspace_integration.workspace_manager.services.base import SquireWorkspaceServiceBase
from gworkspace_integration.workspace_manager.services.users import SquireWorkspaceUserService
from membership_file.models import Member


class SquireWorkspaceGroupService(SquireWorkspaceServiceBase[DirectoryService]):
    """
    All interactions Squire makes with Google Workspace's Directory Service related to
    groups and their members are made here.
    """

    CACHE_KEY_GROUPS = "Squire_WorkspaceGroups"
    CACHE_KEY_GROUPMEMBERS = "Squire_WorkspaceGroupMember-%(groupKey)s"

    def __init__(self, service: DirectoryService, settings, user_service: SquireWorkspaceUserService):
        super().__init__(service, settings)
        self._sync_planner = SquireWorkspaceGroupPlanner(settings)
        self._user_service = user_service

    def groups(self, ignore_cache=False) -> list[WorkspaceGroup]:
        """Fetch all Workspace groups, using the cache if available and allowed"""
        if ignore_cache:
            return list(self._gservice.groups())
        return self.fetch_with_lock(cache_key=self.CACHE_KEY_GROUPS, api_fn=(lambda: list(self._gservice.groups())))

    def group_members(self, group: WorkspaceGroup) -> list[WorkspaceGroupMember]:
        """Fetch all group members of a some workspace group"""
        assert isinstance(group, WorkspaceGroup)
        return self.fetch_with_lock(
            cache_key=self.CACHE_KEY_GROUPMEMBERS % {"groupKey": group.id},
            api_fn=(lambda: list(self._gservice.group_members(group.id))),
        )

    def get_group_for_committee(
        self, committee: AssociationGroup, groups: list[WorkspaceGroup] | None = None
    ) -> WorkspaceGroup | None:
        """Gets the Workspace group that corresponds to the given committee, if any"""
        groups = groups if groups is not None else self.groups()
        for group in groups:
            for alias in group.aliases:
                if alias == f"committee-{committee.pk}@{self.settings.primary_domain}":
                    return group

    def get_committee_for_group(self, group: WorkspaceGroup) -> AssociationGroup | None:
        """Gets the committee that corresponds to the given Workspace group, if any"""
        pattern = re.compile(rf"committee-([0-9]+)@{re.escape(self.settings.primary_domain)}")

        for alias in group.aliases:
            if match := pattern.match(alias):
                if comm := AssociationGroup.objects.filter(pk=int(match.group(1))).first() is not None:
                    return comm

    def get_active_committees(self):
        """Gets a queryset containing all associationGroups that should have an alias setup"""
        return AssociationGroup.objects.filter(
            type__in=[AssociationGroup.COMMITTEE, AssociationGroup.ORDER, AssociationGroup.WORKGROUP],
            contact_email__isnull=False,
            contact_email__endswith=f"@{self.settings.primary_domain}",
        )

    def _get_default_wgroup_member(self, member_proxy: MailingListMemberProxy) -> WorkspaceGroupMember:
        """Gets the default Workspace group member corresponding to a Proxy member"""
        return WorkspaceGroupMember(
            "admin#directory#member",
            member_proxy.email,
            WorkspaceGroupMemberRole.MEMBER,
            type=WorkspaceGroupMemberType.USER,
            delivery_settings=WorkspaceGroupMemberDeliverySettings.ALL_MAIL,
        )

    def _get_wgroup_default_owner(self) -> WorkspaceGroupMember:
        """The default owner for a Workspace group"""
        return WorkspaceGroupMember(
            "admin#directory#member",
            self.settings.directory_admin_username,
            WorkspaceGroupMemberRole.OWNER,
            type=WorkspaceGroupMemberType.USER,
            delivery_settings=WorkspaceGroupMemberDeliverySettings.NONE,
        )

    def _get_wgroup_members_for_mailinglist(
        self, mailing_list: MailingListProxy
    ) -> list[tuple[WorkspaceGroupMember, MailingListMemberProxy]]:
        """Sets up the Workspace group members for a given mailing list (e.g. committee or member alias)"""
        # Make Squire's admin user the group owner. We don't want Workspace admins nor regular users to be owners.
        owner = (
            self._get_wgroup_default_owner(),
            None,
        )

        res = [owner]
        for member_proxy in mailing_list.members:
            res.append((self._get_default_wgroup_member(member_proxy), member_proxy))
        return res

    def get_group_member_syncs(
        self, committee: MailingListProxy, group: WorkspaceGroup
    ) -> Iterator[WorkspaceGroupMemberSync]:
        """Gets the current and desired Workspace group members for a mailing list."""
        current_wgroup_members = self.group_members(group)
        desired_wgroup_members = self._get_wgroup_members_for_mailinglist(committee)

        synced_group_members = self._sync_planner.calc_sync_status_group_members(
            current_wgroup_members, desired_wgroup_members, is_allow_invalid=False
        )

        for sync in synced_group_members:
            if sync.squire_member and sync.squire_member.pk is not None:
                sync.workspace_user = self._user_service.get_user_for_member(sync.squire_member)
            elif sync.wgroup_member.id:
                sync.workspace_user = self._user_service.get_user_by_id(sync.wgroup_member.id)
            # yielding prevents iterating twice: once here, once in the caller (most likely)
            yield sync

    def bulk_sync_group_members(self, committee: MailingListProxy, group: WorkspaceGroup):
        """Modifies the members of a Workspace group corresponding to the given committee. Adds missing members, removes excess members, and updates existing ones."""
        assert group is not None, "Group must be provided."

        # Do not sync invalid committee members
        synced_group_members = self.get_group_member_syncs(committee, group)

        to_update, to_add, to_remove = [], [], []
        for sync in synced_group_members:
            match sync.status:
                case WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_UPDATE:
                    to_update.append(sync.wgroup_member)
                case WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_ADD:
                    to_add.append(sync.wgroup_member)
                case WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_REMOVE:
                    to_remove.append(sync.wgroup_member)
                case WorkspaceGroupMemberSyncStatus.SYNC_INVALID:  # pragma: no cover
                    self.logger.warning(
                        f"Did not sync {sync.wgroup_member.email} to group {group.email}. Email considered invalid!"
                    )

        print(">>>> start SYNC")
        self._gservice.bulk_change_group_members(group.id, to_update, to_add, to_remove)
        # Invalidate cache after batch
        self.invalidate_cache(self.CACHE_KEY_GROUPMEMBERS % {"groupKey": group.id})

    def get_group_for_mailinglist(
        self, email: str, groups: list[WorkspaceGroup] | None = None
    ) -> WorkspaceGroup | None:
        """Gets the Workspace group that corresponds to the given mailing list, if any"""
        groups = groups if groups is not None else self.groups()
        return next((g for g in groups if g.email == email), None)
