import crypt
from secrets import token_urlsafe

from django.utils.text import slugify

from gworkspace_integration.api.formats.users import WorkspaceExternalUserId, WorkspaceUser, WorkspaceUserName
from gworkspace_integration.api.services.directory_service import DirectoryService
from gworkspace_integration.workspace_manager.services.base import SquireWorkspaceServiceBase
from membership_file.models import Member

MemberWorkspaceUserMap = dict[Member, WorkspaceUser | None]
WorkspaceUserMemberMap = dict[WorkspaceUser, Member | None]


class SquireWorkspaceUserService(SquireWorkspaceServiceBase[DirectoryService]):
    """
    All interactions Squire makes with Google Workspace's Directory Service related to
    users are made here.
    """

    CACHE_KEY_USERS = "Squire_WorkspaceUsers"
    CACHE_KEY_EXTRA_USER = "Squire_WorkspaceUser-%(userKey)s"

    # -------
    # FETCH USER
    # -------
    def users(self, ignore_cache=False) -> list[WorkspaceUser]:
        """Fetch all Workspace users, using the cache if available and allowed"""
        if ignore_cache:
            return list(self._gservice.users())
        return self.fetch_with_lock(cache_key=self.CACHE_KEY_USERS, api_fn=(lambda: list(self._gservice.users())))

    def get_user_by_id(self, id: str, users: list[WorkspaceUser] | None = None) -> WorkspaceUser | None:
        """Gets a Workspace User uniquely identified by the given Google Workspace id"""
        users = users if users is not None else self.users()
        user = next(filter(lambda u: u.id == id, users), None)
        if user is not None:
            return user

        # User not found; it might be outside our members OU
        return self.fetch_with_lock(
            cache_key=self.CACHE_KEY_EXTRA_USER % {"userKey": id}, api_fn=(lambda: self._gservice.user(id))
        )

    def get_user_for_member(self, member: Member, users: list[WorkspaceUser] | None = None) -> WorkspaceUser | None:
        """Gets the Workspace user that corresponds to the given member, if any"""
        users = users if users is not None else self.users()
        for user in users:
            for eid in user.external_ids:
                if eid.type == "organization" and eid.value == str(member.pk):
                    return user

    def get_member_for_user(self, user: WorkspaceUser) -> Member | None:
        """Gets the member that corresponds to the given Workspace user, if any"""
        for eid in user.external_ids:
            if eid.type == "organization":
                return Member.objects.filter(pk=int(eid.value)).first()

    # -------
    # ADD USER
    # -------
    def _generate_username(self, member: Member, users: list[WorkspaceUser], max_attempts=10) -> None | str:
        """
        Generates a unique username for the given member. This can happen if multiple
        members share the same name.

        E.g. John Doe already exists as john.doe@example.com
        Another John Doe will get username john.doe2@example.com

        Assumes there is no pre-existing workspace user for the given member.

        :return: If creation fails `max_attempts` times, returns `None`. Otherwise returns the username
        """
        name = f"{member.first_name}-{member.tussenvoegsel}{member.last_name}"
        name = slugify(member.get_full_name(allow_spoof=False).replace(" ", "")).replace("-", ".")
        suffix = "@" + self.settings.primary_domain
        requested_name = name + suffix

        valid_name_found = True
        for i in range(1, max(max_attempts + 1, 2)):
            valid_name_found = True
            for user in users:
                if user.primaryEmail == requested_name:
                    # Username already in use, try again with the next digit. E.g. foo1@example.com
                    requested_name = name + str(i) + suffix
                    valid_name_found = False
                    break

        if not valid_name_found:
            self.logger.warning(
                f"Unable to generate variant username {name + suffix} for member {member.get_full_name(allow_spoof=False)} ({member.pk}). Stopped after {max_attempts} attempts"
            )
            return None
        return requested_name

    def _create_user_for_member(
        self, member: Member, users: list[WorkspaceUser], clear_cache=True
    ) -> WorkspaceUser | None:
        """
        Creates a Workspace User for the given member. A list of existing `users` should
        be passed to resolve naming conflicts.

        :param clear_cache: whether to clear the cache after a write (defaults to True)
        """
        last_name = member.last_name
        if member.tussenvoegsel:
            last_name = member.tussenvoegsel + " " + last_name

        username = self._generate_username(member, users)
        if username is None:
            return None

        user = WorkspaceUser(
            primaryEmail=username,
            hashFunction="crypt",
            password=crypt.crypt(token_urlsafe(32), salt=crypt.METHOD_SHA512),
            changePasswordAtNextLogin=True,
            recoveryEmail=member.email,
            includeInGlobalAddressList=False,
            archived=False,
            suspended=False,
            name=WorkspaceUserName(givenName=member.first_name, familyName=last_name),
            external_ids=[WorkspaceExternalUserId(type="organization", value=member.pk)],
            orgUnitPath=self.settings.members_ou,
        )
        self._gservice.add_user(user)
        if clear_cache:
            self.invalidate_cache(self.CACHE_KEY_USERS)
        return user

    def bulk_create_users_for_members(self, members: list[Member]):
        """
        Bulk create Workspace users for the given members.
        """
        # Fetch all users (from cache if possible)
        users = self.users()
        new_users = []

        for member in members:
            user = self._create_user_for_member(member, users, clear_cache=False)
            if user is not None:
                new_users.append(user)

        # Invalidate cache after batch (if needed)
        if new_users:
            self.invalidate_cache(self.CACHE_KEY_USERS)
        return new_users

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
