import crypt
from enum import Enum
import re
from secrets import token_urlsafe
import time
from typing import Callable, TypeVar, cast

from django.apps import apps
from django.core.cache import cache
from django.utils.text import slugify

from committees.models import AssociationGroup
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
from membership_file.models import Member

T = TypeVar("T")
MemberWorkspaceUserMap = dict[Member, WorkspaceUser | None]
WorkspaceUserMemberMap = dict[WorkspaceUser, Member | None]


def get_workspace_manager() -> "SquireGoogleWorkspaceManager | None":
    """Access the AppConfig to obtain Squire's Google Workspace Manager that connects to the Google Workspace API."""
    return cast(GworkspaceIntegrationConfig, apps.get_app_config("gworkspace_integration")).workspace_client


class WorkspaceGroupMemberSyncStatus(Enum):
    """What needs to happen to a Workspace Group Member in order for it to be synced with Squire"""

    SYNC_UP_TO_DATE = 0
    SYNC_SHOULD_UPDATE = 1
    SYNC_SHOULD_ADD = 2
    SYNC_SHOULD_REMOVE = 3


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

    def __init__(self):
        settings = GoogleWorkspaceSettings.from_json("squire/config/gworkspaceconfig.json")
        self._client = GoogleWorkspaceClient(settings)

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
        suffix = "@" + self._client._domain
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

    def get_user_for_member(self, member: Member, users: list[WorkspaceUser] | None = None) -> WorkspaceUser | None:
        """Gets the user that corresponds to the given member, if any"""
        users = users or self.users()
        for user in users:
            for eid in user.external_ids:
                if eid.type == "organization" and eid.value == str(member.pk):
                    return user

    def get_member_for_user(self, user: WorkspaceUser) -> Member | None:
        """Gets the member that corresponds to the given user, if any"""
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
            orgUnitPath=self._client._members_ou,
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
        """Gets the group that corresponds to the given committee, if any"""
        groups = groups or self.groups()
        for group in groups:
            for alias in group.aliases:
                if alias == f"committee-{committee.pk}@{self._client._domain}":
                    return group

    def get_committee_for_group(self, group: WorkspaceGroup) -> AssociationGroup | None:
        """Gets the member that corresponds to the given user, if any"""
        pattern = re.compile(rf"committee-([0-9]+)@{re.escape(self._client._domain)}")
        for alias in group.aliases:
            if pattern.match(alias):
                return AssociationGroup().objects.filter(pk=int(pattern.group(1))).first()

    def get_active_committees(self):
        """Gets a queryset containing all associationGroups that should have an alias setup"""
        return AssociationGroup.objects.filter(
            type__in=[AssociationGroup.COMMITTEE, AssociationGroup.ORDER, AssociationGroup.WORKGROUP],
            contact_email__isnull=False,
            contact_email__endswith=f"@{self._client._domain}",
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
        TODO
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

    def _get_group_member(self, email: str) -> WorkspaceGroupMember:
        """TODO"""
        return WorkspaceGroupMember(
            email=email,
            role=WorkspaceGroupMemberRole.MEMBER,
            type=WorkspaceGroupMemberType.USER,
            delivery_settings=WorkspaceGroupMemberDeliverySettings.ALL_MAIL,
        )

    def get_group_members_for_committee(self, committee: AssociationGroup) -> list[WorkspaceGroupMember]:
        """TODO"""
        owner = WorkspaceGroupMember(
            email=self._client._admin,
            role=WorkspaceGroupMemberRole.OWNER,
            type=WorkspaceGroupMemberType.USER,
            delivery_settings=WorkspaceGroupMemberDeliverySettings.NONE,
        )
        return [owner] + [self._get_group_member(m.email) for m in committee.members.all()]

    def get_sync_status(self, group: WorkspaceGroup, new_group_members: list[WorkspaceGroupMember]):
        """TODO"""

        current_group_members = self.group_members(group)
        new_group_members = set(new_group_members)
        res: list[tuple[WorkspaceGroupMember, WorkspaceGroupMemberSyncStatus]] = []

        for current_member in current_group_members:
            assert current_member.id != ""
            member = next(filter(lambda m: m.email == current_member.email, new_group_members), None)
            if member is None:
                # Current group member isn't one of the new group members; remove it
                res.append((current_member, WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_REMOVE))
                continue

            # This group member is already part of the group currently, and should remain so. Clean it up.
            new_group_members.remove(member)
            if current_member.role != member.role or current_member.type != member.type:
                # Info is out of date!
                res.append((member, WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_UPDATE))
                continue
            res.append((member, WorkspaceGroupMemberSyncStatus.SYNC_UP_TO_DATE))

        # All unmatched new group members should still be added
        for new_member in new_group_members:
            res.append((new_member, WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_ADD))

        return res

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


