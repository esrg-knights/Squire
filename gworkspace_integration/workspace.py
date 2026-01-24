import crypt
from enum import Enum
import logging
import re
from secrets import token_urlsafe
import time
from typing import Callable, Iterable, TypeVar, cast

from django.apps import apps
from django.core.cache import cache
from django.db.models import QuerySet
from django.utils.text import slugify

from committees.email import MemberMailingListAlias, get_email_settings
from committees.models import AssociationGroup, AssociationGroupMembership
from gworkspace_integration.admin_status.proxy import MailingListMemberProxy, MailingListProxy
from gworkspace_integration.api.client import GoogleWorkspaceClient, GoogleWorkspaceSettings
from gworkspace_integration.api.formats.groups import (
    WorkspaceGroup,
    WorkspaceGroupContactPermissions,
    WorkspaceGroupDefaultSender,
    WorkspaceGroupDiscoverPermissions,
    WorkspaceGroupJoinPermissions,
    WorkspaceGroupLeavePermissions,
    WorkspaceGroupMember,
    WorkspaceGroupMemberDeliverySettings,
    WorkspaceGroupMemberRole,
    WorkspaceGroupMemberType,
    WorkspaceGroupModerationPermissions,
    WorkspaceGroupPostPermissions,
    WorkspaceGroupReplyTo,
    WorkspaceGroupSettings,
    WorkspaceGroupViewPermissions,
    WorkspaceGroupViewPermissionsExt,
)
from gworkspace_integration.api.formats.users import WorkspaceExternalUserId, WorkspaceUser, WorkspaceUserName
from gworkspace_integration.apps import GworkspaceIntegrationConfig
from gworkspace_integration.workspace_manager.groups import WorkspaceGroupMemberSync, WorkspaceGroupMemberSyncStatus
from membership_file.models import Member

T = TypeVar("T")
MemberWorkspaceUserMap = dict[Member, WorkspaceUser | None]
WorkspaceUserMemberMap = dict[WorkspaceUser, Member | None]


def get_workspace_manager() -> "SquireGoogleWorkspaceManager | None":
    """Access the AppConfig to obtain Squire's Google Workspace Manager that connects to the Google Workspace API."""
    return cast(GworkspaceIntegrationConfig, apps.get_app_config("gworkspace_integration")).workspace_client


class WorkspaceCacheManager:
    """
    Helper class to reduce the number of expensive API calls through a (shared) cache.
    Requires Memcached to be setup to properly share the cache between multiple
    (Gunicorn) processes.
    """

    LOCK_TIMEOUT = 30  # seconds

    @classmethod
    def fetch_with_lock(
        cls,
        api_fn: Callable[[], T],
        cache_key: str,
        cache_timeout=3600,
        lock_key: str | None = None,
        retries: int = 5,
        retry_delay: float = 0.5,
        raise_timeout=True,
    ) -> T:
        """
        Fetch data from an API and add it to a cache. Subsequent calls with the same cache key
        will retrieve from the cache instead. Use this to reduce the number of API calls.
        If the data is not in cache, fetch the data from the API and lock.

        :param api_fn: function to rebuild the value if missing.
        :param cache_key: key to store/retrieve the cached value
        :param cache_timeout: TTL for cached value
        :param lock_key: optional lock key (defaults to cache_key + "_lock")
        :param retries: how many times to wait if another process is already refilling the cache
        :param retry_delay: delay between retries (in seconds)
        :param raise_timeout: whether to raise an exception on timeout or call `fetch_func` anyway

        :raise TimeoutError: if all the following conditions are met:

        - `raise_timeout=True`
        - the value was not present in the cache
        - another process is already calling `fetch_func` to retrieve from the cache
        - this other process is taking too long to do so (longer than `retries * retry_delay` seconds)
        """
        lock_key = lock_key or f"{cache_key}_lock"

        # Try to read from cache first
        data = cache.get(cache_key)
        if data is not None:
            return data

        # Avoid race conditions and acquire a lock. add(..) is atomic
        if cache.add(lock_key, True, timeout=cls.LOCK_TIMEOUT):
            try:
                # Call function and add to cache
                data = api_fn()
                cache.set(cache_key, data, timeout=cache_timeout)
                return data
            finally:
                # Release lock
                cache.delete(lock_key)
        else:
            # Another process is currently fetching the data
            for _ in range(retries):
                time.sleep(retry_delay)
                data = cache.get(cache_key)
                if data is not None:
                    return data
            # Took too long!
            if raise_timeout:
                raise TimeoutError(
                    f"Unable to retrieve workspace user list from cache. Another process was updating it but took too long!"
                )
            return api_fn()


class SquireGoogleWorkspaceManager:
    """
    All interactions Squire makes with the Google Workspace API are handled through this class.
    It is responsible for adding members' emails to a group of member aliases (depending
    on their stored preferences), and adding members' emails to the aliases of committees
    they are in.

    Utilises caching to prevent subsequent API calls from fetching the same data.
    """

    CACHE_KEY_USERS = "Squire_WorkspaceUsers"
    CACHE_KEY_GROUPS = "Squire_WorkspaceGroups"
    CACHE_KEY_GROUPMEMBERS = "Squire_WorkspaceGroupMember-%(groupKey)s"

    logger = logging.getLogger("squire_gworkspace")

    def __init__(self):
        settings = GoogleWorkspaceSettings.from_json("squire/config/gworkspaceconfig.json")
        self._client = GoogleWorkspaceClient(settings)
        self._email_mgr = get_email_settings()
        assert self._email_mgr is not None, "Cannot load Google Workspace Manager; email settings missing!"

    # -----------------------
    # USERS
    # -----------------------
    def _generate_username(self, member: Member, users: list[WorkspaceUser]):
        """
        Generates a unique username for the given member. This can happen if multiple
        members share the same name.

        E.g. John Doe already exists as john.doe@example.com
        Another John Doe will get username john.doe2@example.com

        Assumes there is no pre-existing workspace user for the given member
        """
        name = f"{member.first_name}-{member.tussenvoegsel}{member.last_name}"
        name = slugify(member.get_full_name().replace(" ", "")).replace("-", ".")
        suffix = "@" + self._client.domain
        requested_name = name + suffix
        counter = 0

        for user in users:
            if user.primaryEmail == requested_name:
                counter += 1
                requested_name = name + str(counter) + suffix
        return requested_name

    def users(self, ignore_cache=False) -> list[WorkspaceUser]:
        """Fetch all Workspace users, using the cache if available and allowed"""
        if ignore_cache:
            return list(self._client.DirectoryService.users())

        return WorkspaceCacheManager.fetch_with_lock(
            cache_key=self.CACHE_KEY_USERS,
            api_fn=(lambda: list(self._client.DirectoryService.users())),
        )

    def get_user_for_member(
        self, member: MailingListMemberProxy, users: list[WorkspaceUser] | None = None
    ) -> WorkspaceUser | None:
        """Gets the Workspace user that corresponds to the given member, if any"""
        users = users or self.users()
        for user in users:
            for eid in user.external_ids:
                if eid.type == "organization" and eid.value == str(member.pk):
                    return user

    def get_member_for_user(self, user: WorkspaceUser) -> Member | None:
        """Gets the member that corresponds to the given Workspace user, if any"""
        for eid in user.external_ids:
            if eid.type == "organization":
                return Member.objects.filter(pk=int(eid.value)).first()

    def _create_user_for_member(self, member: Member, users: list[WorkspaceUser], clear_cache=True):
        """
        Creates a Workspace User for the given member. A list of existing `users` should
        be passed to resolve naming conflicts.

        :param clear_cache: whether to clear the cache after a write (defaults to True)
        """
        last_name = member.last_name
        if member.tussenvoegsel:
            last_name = member.tussenvoegsel + " " + last_name
        user = WorkspaceUser(
            primaryEmail=self._generate_username(member, users),
            hashFunction="crypt",
            password=crypt.crypt(token_urlsafe(32), salt=crypt.METHOD_SHA512),
            changePasswordAtNextLogin=True,
            recoveryEmail=member.email,
            includeInGlobalAddressList=False,
            archived=False,
            suspended=False,
            name=WorkspaceUserName(givenName=member.first_name, familyName=last_name),
            external_ids=[WorkspaceExternalUserId(type="organization", value=member.pk)],
            orgUnitPath=self._client.members_ou,
        )
        self._client.DirectoryService.add_user(user)
        if clear_cache:
            cache.delete(self.CACHE_KEY_USERS)
        return user

    def bulk_create_users_for_members(self, members: list[Member]):
        """
        Bulk create Workspace users for the given members.
        """
        # Fetch all users (from cache if possible)
        users = self.users()

        for member in members:
            user = self._create_user_for_member(member, users, clear_cache=False)
            users.append(user)

        # Invalidate cache after batch
        cache.delete(self.CACHE_KEY_USERS)
        return users

    # -----------------------
    # GROUPS
    # -----------------------
    def get_group_for_committee(
        self, committee: AssociationGroup, groups: list[WorkspaceGroup] | None = None
    ) -> WorkspaceGroup | None:
        """Gets the Workspace group that corresponds to the given committee, if any"""
        groups = groups or self.groups()
        for group in groups:
            for alias in group.aliases:
                if alias == f"committee-{committee.pk}@{self._client.domain}":
                    return group

    def get_committee_for_group(self, group: WorkspaceGroup) -> AssociationGroup | None:
        """Gets the member that corresponds to the given user, if any"""
        pattern = re.compile(rf"committee-([0-9]+)@{re.escape(self._client.domain)}")
        for alias in group.aliases:
            if pattern.match(alias):
                return AssociationGroup().objects.filter(pk=int(pattern.group(1))).first()

    def get_active_committees(self):
        """Gets a queryset containing all associationGroups that should have an alias setup"""
        return AssociationGroup.objects.filter(
            type__in=[AssociationGroup.COMMITTEE, AssociationGroup.ORDER, AssociationGroup.WORKGROUP],
            contact_email__isnull=False,
            contact_email__endswith=f"@{self._client.domain}",
        )

    def groups(self, ignore_cache=False) -> list[WorkspaceGroup]:
        """Fetch all Workspace groups, using the cache if available and allowed"""
        if ignore_cache:
            return list(self._client.DirectoryService.groups())
        return WorkspaceCacheManager.fetch_with_lock(
            cache_key=self.CACHE_KEY_GROUPS,
            api_fn=(lambda: list(self._client.DirectoryService.groups())),
        )

    def group_members(self, group: WorkspaceGroup) -> list[WorkspaceGroupMember]:
        """Fetch all group members of a some workspace group"""
        assert isinstance(group, WorkspaceGroup)
        return WorkspaceCacheManager.fetch_with_lock(
            cache_key=self.CACHE_KEY_GROUPMEMBERS % {"groupKey": group.id},
            api_fn=(lambda: list(self._client.DirectoryService.group_members(group.id))),
        )

    def get_member_user_mappings(self) -> tuple[MemberWorkspaceUserMap, MemberWorkspaceUserMap]:
        """
        Build a mapping from Squire members to Workspace users, and vice versa.
        """
        users = self.users()
        # Map all relevant members to Workspace Users
        members = Member.objects.filter_active().order_by("first_name", "last_name")
        member_map: MemberWorkspaceUserMap = {}
        for member in members:
            member_map[member] = self.get_user_for_member(member, users)

        # There might be additional users that don't correspond to (active) members. Link these here.
        user_map: WorkspaceUserMemberMap = {v: k for k, v in member_map.items() if v is not None}
        for user in users:
            if user not in user_map:
                user_map[user] = self.get_member_for_user(user)

        return member_map, user_map

    def get_user_by_email(self, email: str, users: list[WorkspaceUser] | None = None) -> WorkspaceUser | None:
        """Gets a Workspace User uniquely identified by the given email address"""
        users = users or self.users()
        return next(filter(lambda u: u.primaryEmail == email, users), None)

    def get_user_by_id(self, id: str, users: list[WorkspaceUser] | None = None) -> WorkspaceUser | None:
        """Gets a Workspace User uniquely identified by the given Google Workspace id"""
        users = users or self.users()
        return next(filter(lambda u: u.id == id, users), None)

    def _get_wgroup_member(
        self, squire_member: Member, workspace_user: WorkspaceUser | None = None
    ) -> WorkspaceGroupMember:
        """Gets the Workspace group member corresponding to a Squire member"""
        return WorkspaceGroupMember(
            "admin#directory#member",
            squire_member.email,
            WorkspaceGroupMemberRole.MEMBER,
            type=WorkspaceGroupMemberType.USER,
            delivery_settings=WorkspaceGroupMemberDeliverySettings.ALL_MAIL,
            **({"id": workspace_user.id} if workspace_user is not None else {}),
        )

    def _get_group_members_sync_for_committee(self, committee: MailingListProxy) -> list[WorkspaceGroupMemberSync]:
        """Build a group member sync for all Squire members of a committee"""
        # Make Squire's admin user the group owner. We don't want Workspace admins to be owners.
        owner = WorkspaceGroupMemberSync(
            WorkspaceGroupMember(
                "admin#directory#member",
                self._client.admin_username,
                WorkspaceGroupMemberRole.OWNER,
                type=WorkspaceGroupMemberType.USER,
                delivery_settings=WorkspaceGroupMemberDeliverySettings.NONE,
            )
        )

        res = [owner]
        for member_proxy in committee.members:
            workspace_user = self.get_user_for_member(member_proxy) if member_proxy.pk is not None else None
            res.append(
                WorkspaceGroupMemberSync(
                    self._get_wgroup_member(member_proxy, workspace_user),
                    WorkspaceGroupMemberSyncStatus.SYNC_UP_TO_DATE,
                    workspace_user,
                    member_proxy,
                )
            )
        return res

    def is_email_valid_for_sync(self, email: str) -> bool:
        """Whether a Workspace group member can be synced"""
        if email == self._client.admin_username:
            return True

        return not email.endswith(self._client.domain) and not any(
            email.endswith(domain) for domain in self._client.workspace_domains
        )

    def calc_sync_status_group_members(
        self,
        group: WorkspaceGroup,
        committee: MailingListProxy,
        is_allow_invalid=False,
    ) -> list[WorkspaceGroupMemberSync]:
        """
        Gets a "diff" of a given Workspace group, and how that group should be populated according to a committee.
        Sync statuses include up-to-date, additions (not present in the Workspace group, but should be due to the
        committee), removals (present in the Workspace group, but shouldn't), and updates (e.g. in OWNER/MEMBER-roles)

        The resulting list is sorted in the following order: sync status, role, name, email
        """

        current_workspace_members = set(self.group_members(group))
        committee_members_sync = self._get_group_members_sync_for_committee(committee)

        for cmember_sync in committee_members_sync:
            # Match based on email; this is the unique identifier for a group member in Google Workspace
            # Workspace Users shouldn't directly be added to these groups; we wish to include the members' non-Workspace emails
            current_wgroup_member = next(
                filter(lambda m: m.email == cmember_sync.wgroup_member.email, current_workspace_members), None
            )

            if current_wgroup_member is None:
                # No corresponding workspace member found to a current committee member. It should be added!
                cmember_sync.status = WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_ADD
                continue

            # GroupMember was found. Remove it so we are left with the Workspace members that do not have a corresponding Squire member.
            current_workspace_members.remove(current_wgroup_member)

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
        for gmember_to_remove in current_workspace_members:
            committee_members_sync.append(
                WorkspaceGroupMemberSync(
                    gmember_to_remove,
                    WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_REMOVE,
                    workspace_user=self.get_user_by_id(gmember_to_remove.id),
                )
            )

        if not is_allow_invalid:
            for sync in committee_members_sync:
                if not self.is_email_valid_for_sync(sync.wgroup_member.email):
                    sync.status = WorkspaceGroupMemberSyncStatus.SYNC_INVALID

        # Sort based on sync status, role, name, email
        return sorted(
            committee_members_sync,
            key=lambda x: (
                x.status.value,
                {
                    WorkspaceGroupMemberRole.OWNER: 0,
                    WorkspaceGroupMemberRole.MANAGER: 1,
                    WorkspaceGroupMemberRole.MEMBER: 2,
                }.get(x.wgroup_member.role.value, 9),
                (
                    x.squire_member.name
                    if x.squire_member
                    else (x.workspace_user.name.fullName if x.workspace_user else "")
                ),
                x.wgroup_member.email,
            ),
        )

    def bulk_sync_group_members(self, committee: MailingListProxy, group: WorkspaceGroup):
        """Modifies the members of a Workspace group corresponding to the given committee. Adds missing members, removes excess members, and updates existing ones."""
        assert (
            group is not None
        ), "Attempting to sync Workspace group members for committee, but such Workspace group did not yet exist."

        # Do not sync invalid committee members
        synced_group_members = self.calc_sync_status_group_members(group, committee, is_allow_invalid=False)

        print(synced_group_members)
        print(">>>> start SYNC")
        self._client.DirectoryService.bulk_change_group_members(
            group.id,
            map(
                lambda x: x.wgroup_member,
                filter(lambda x: x.status == WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_UPDATE, synced_group_members),
            ),
            map(
                lambda x: x.wgroup_member,
                filter(lambda x: x.status == WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_ADD, synced_group_members),
            ),
            map(
                lambda x: x.wgroup_member,
                filter(lambda x: x.status == WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_REMOVE, synced_group_members),
            ),
        )
        # Invalidate cache after batch
        cache.delete(self.CACHE_KEY_GROUPMEMBERS % {"groupKey": group.id})

    # -----------------------
    # GROUPS (MEMBER MAILING LISTS)
    # -----------------------
    def get_group_for_mailinglist(
        self, email: str, groups: list[WorkspaceGroup] | None = None
    ) -> WorkspaceGroup | None:
        """Gets the Workspace group that corresponds to the given mailing list, if any"""
        groups = groups or self.groups()
        return next((g for g in groups if g.email == email), None)

    def _get_committee_settings(self, committee: AssociationGroup, receive_only=False) -> WorkspaceGroupSettings:
        """Gets group settings that can be used for committee groups"""
        return WorkspaceGroupSettings(
            committee.contact_email,
            name="group name",
            description="group description",
            whoCanJoin=WorkspaceGroupJoinPermissions.INVITED_CAN_JOIN,
            whoCanViewMembership=WorkspaceGroupViewPermissions.ALL_OWNERS_CAN_VIEW,
            whoCanViewGroup=WorkspaceGroupViewPermissionsExt.ALL_MANAGERS_CAN_VIEW,
            allowExternalMembers=True,
            whoCanPostMessage=WorkspaceGroupPostPermissions.ALL_MANAGERS_CAN_POST,
            allowWebPosting=True,
            replyTo=WorkspaceGroupReplyTo.REPLY_TO_SENDER,
            includeCustomFooter=True,
            customFooterText="You can manage your subscriptions for this email and all other emails in Squire. You can Unsubscribe there! <insert link>",
            membersCanPostAsTheGroup=False,
            includeInGlobalAddressList=False,
            whoCanLeaveGroup=WorkspaceGroupLeavePermissions.NONE_CAN_LEAVE,
            whoCanContactOwner=WorkspaceGroupContactPermissions.ALL_MANAGERS_CAN_CONTACT,
            whoCanModerateMembers=WorkspaceGroupModerationPermissions.OWNERS_ONLY,
            whoCanModerateContent=WorkspaceGroupModerationPermissions.OWNERS_AND_MANAGERS,
            whoCanAssistContent=WorkspaceGroupModerationPermissions.OWNERS_AND_MANAGERS,
            enableCollaborativeInbox=False,
            whoCanDiscoverGroup=WorkspaceGroupDiscoverPermissions.ALL_MEMBERS_CAN_DISCOVER,
            defaultSender=WorkspaceGroupDefaultSender.DEFAULT_SELF,
        )

    def _get_mailinglist_settings(self, email: str) -> WorkspaceGroupSettings:
        """Gets group settings that can be used for mailing lists"""
        return WorkspaceGroupSettings(
            email,
            name="group name",
            description="group description",
            whoCanJoin=WorkspaceGroupJoinPermissions.INVITED_CAN_JOIN,
            whoCanViewMembership=WorkspaceGroupViewPermissions.ALL_OWNERS_CAN_VIEW,
            whoCanViewGroup=WorkspaceGroupViewPermissionsExt.ALL_MANAGERS_CAN_VIEW,
            allowExternalMembers=True,
            whoCanPostMessage=WorkspaceGroupPostPermissions.ALL_MANAGERS_CAN_POST,
            allowWebPosting=True,
            replyTo=WorkspaceGroupReplyTo.REPLY_TO_SENDER,
            includeCustomFooter=True,
            customFooterText="You can manage your subscriptions for this email and all other emails in Squire. You can Unsubscribe there! <insert link>",
            membersCanPostAsTheGroup=False,
            includeInGlobalAddressList=False,
            whoCanLeaveGroup=WorkspaceGroupLeavePermissions.NONE_CAN_LEAVE,
            whoCanContactOwner=WorkspaceGroupContactPermissions.ALL_MANAGERS_CAN_CONTACT,
            whoCanModerateMembers=WorkspaceGroupModerationPermissions.OWNERS_ONLY,
            whoCanModerateContent=WorkspaceGroupModerationPermissions.OWNERS_AND_MANAGERS,
            whoCanAssistContent=WorkspaceGroupModerationPermissions.OWNERS_AND_MANAGERS,
            enableCollaborativeInbox=False,
            whoCanDiscoverGroup=WorkspaceGroupDiscoverPermissions.ALL_MEMBERS_CAN_DISCOVER,
            defaultSender=WorkspaceGroupDefaultSender.DEFAULT_SELF,
        )

    def create_mailinglist(self, email: str, receivers: list[str]) -> WorkspaceGroup:
        """Creates a google group that serves as a mailing list. E.g. leden@example.com to email all members"""


# "allowExternalMembers": False
# "allowWebPosting": False
# "enableCollaborativeInbox": False
# "includeInGlobalAddressList": False
# "membersCanPostAsTheGroup": False
# "messageModerationLevel": "MODERATE_NONE"
# "spamModerationLevel": "MODERATE"
# "whoCanAdd": "ALL_MANAGERS_CAN_ADD"
# "whoCanDiscoverGroup": "ALL_MEMBERS_CAN_DISCOVER"
# "whoCanJoin": "INVITED_CAN_JOIN"
# "whoCanLeaveGroup": "NONE_CAN_LEAVE"
# "whoCanModerateContent": "ALL_MEMBERS"
# "whoCanModerateMembers": "OWNERS_AND_MANAGERS"
# "whoCanPostMessage": "ANYONE_CAN_POST"
# "whoCanViewGroup": "ALL_MEMBERS_CAN_VIEW"
# "whoCanViewMembership": "ALL_MEMBERS_CAN_VIEW"
