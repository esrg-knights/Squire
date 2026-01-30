from unittest.mock import Mock

from django.test import TestCase

from core.tests.util import suppress_warnings
from gworkspace_integration.api.formats.users import WorkspaceExternalUserId, WorkspaceUser
from gworkspace_integration.tests.util import SquireServiceTestMixin
from gworkspace_integration.workspace_manager.services.users import SquireWorkspaceUserService
from membership_file.models import Member


class SquireUserServiceTestCase(SquireServiceTestMixin[SquireWorkspaceUserService], TestCase):
    """Tests user service"""

    service_class = SquireWorkspaceUserService

    def test_users(self):
        """Tests fetching users"""
        self._gservice_mock.users.return_value = ["5"]

        res = self._service.users(True)
        self._cache_fetch.assert_not_called()
        self._gservice_mock.users.assert_called_once()
        self.assertListEqual(res, ["5"])

        self._gservice_mock.reset_mock()
        self._service.users(False)
        self._cache_fetch.assert_called_once()
        self._gservice_mock.users.assert_called_once()
        self.assertListEqual(res, ["5"])

    def test_user_by_id(self):
        """Tests fetching a user by ID"""
        users = [WorkspaceUser(id="1"), WorkspaceUser(id="5"), WorkspaceUser(id="9")]
        self._gservice_mock.users.return_value = users
        self.assertEqual(self._service.get_user_by_id("5"), users[1])

    def test_user_member(self):
        """Tests fetching a user for a given member"""
        member = Member.objects.create(email="1@example.com")
        users = [
            WorkspaceUser(id=str(member.pk)),
            WorkspaceUser(id="1", external_ids=[WorkspaceExternalUserId(type="customer", value=str(member.pk))]),
            WorkspaceUser(id="1", external_ids=[WorkspaceExternalUserId(type="organization", value="42")]),
            WorkspaceUser(id="2", external_ids=[WorkspaceExternalUserId(type="organization", value=str(member.pk))]),
        ]
        self.assertEqual(self._service.get_user_for_member(member, users), users[3])
        self.assertIsNone(self._service.get_user_for_member(Member.objects.create(), users))

    def test_member_user(self):
        """Tests fetching a member for a given user"""
        Member.objects.create(email="1@example.com")
        Member.objects.create(email="2@example.com")
        member = Member.objects.create(email="3@example.com")

        user = WorkspaceUser(
            id="2",
            external_ids=[
                WorkspaceExternalUserId(type="customer", value="40"),
                WorkspaceExternalUserId(type="organization", value=str(member.pk)),
            ],
        )
        self.assertEqual(self._service.get_member_for_user(user), member)
        user.external_ids = []
        self.assertIsNone(self._service.get_member_for_user(user))

    def test_member_user_map(self):
        """Tests fetching user-member pairs"""
        member_mapped = Member.objects.create(email="1@example.com")
        member_unmapped = Member.objects.create(email="2@example.com")

        users = [
            WorkspaceUser(id=str(member_mapped.pk)),
            WorkspaceUser(
                id="1", external_ids=[WorkspaceExternalUserId(type="customer", value=str(member_mapped.pk))]
            ),
            WorkspaceUser(id="1", external_ids=[WorkspaceExternalUserId(type="organization", value="42")]),
            WorkspaceUser(
                id="2", external_ids=[WorkspaceExternalUserId(type="organization", value=str(member_mapped.pk))]
            ),
        ]
        self._gservice_mock.users.return_value = users

        # Valid pair
        member_map, user_map = self._service.get_member_user_mappings()
        self.assertIn(member_mapped, member_map)
        self.assertEqual(member_map[member_mapped], users[3])

        self.assertIn(users[3], user_map)
        self.assertEqual(user_map[users[3]], member_mapped)

        # Invalid pair
        self.assertIn(member_unmapped, member_map)
        self.assertIsNone(member_map[member_unmapped])

        self.assertIn(users[0], user_map)
        self.assertIsNone(user_map[users[0]])

    @suppress_warnings(logger_name="squire_gworkspace.SquireWorkspaceUserService")
    def test_generate_username(self):
        """Tests generating usernames"""
        # Simple case
        member_simple = Member(first_name="John", tussenvoegsel="van der", last_name="Doe")
        self.assertEqual(self._service._generate_username(member_simple, []), "johnvanderdoe@example.com")

        # Weird characters
        member_weird = Member(first_name="Jo'hn", tussenvoegsel="van der", last_name="D🍐oe")
        self.assertEqual(self._service._generate_username(member_weird, []), "johnvanderdoe@example.com")

        # Username already in use; multiple John Doe's exist!
        user_0 = WorkspaceUser(primaryEmail="johnvanderdoe@example.com")
        user_1 = WorkspaceUser(primaryEmail="johnvanderdoe1@example.com")
        user_3 = WorkspaceUser(primaryEmail="johnvanderdoe3@example.com")

        # Next in line
        self.assertEqual(
            self._service._generate_username(member_simple, [user_3, user_0]), "johnvanderdoe1@example.com"
        )
        self.assertEqual(
            self._service._generate_username(member_weird, [user_3, user_0]), "johnvanderdoe1@example.com"
        )

        # Multiple already in use (unlikely in practise)
        self.assertEqual(
            self._service._generate_username(member_simple, [user_3, user_1, user_0]), "johnvanderdoe2@example.com"
        )
        self.assertEqual(
            self._service._generate_username(member_weird, [user_3, user_1, user_0]), "johnvanderdoe2@example.com"
        )

        # Creation fails
        self.assertIsNone(self._service._generate_username(member_simple, [user_0], max_attempts=0))
        self.assertIsNone(self._service._generate_username(member_weird, [user_0], max_attempts=0))

    def test_add(self):
        """Tests adding a member as a WorkspaceUser"""
        self._gservice_mock.users.return_value = []
        self._service.invalidate_cache = Mock()
        member = Member(first_name="John", tussenvoegsel="van der", last_name="Doe", email="foo@voorbeeld.nl")
        user: WorkspaceUser = self._service._create_user_for_member(member, [], clear_cache=False)
        self._service.invalidate_cache.assert_not_called()
        user: WorkspaceUser = self._service._create_user_for_member(member, [], clear_cache=True)
        self._service.invalidate_cache.assert_called_once()
        self._service.invalidate_cache.reset_mock()

        # We don't care about all the implementation-specific details. Do the bare minimum of checks.
        self.assertIsNotNone(user)
        self.assertEqual(user.primaryEmail, "johnvanderdoe@example.com")
        self.assertEqual(user.recoveryEmail, "foo@voorbeeld.nl")
        self.assertEqual(user.orgUnitPath, self._service.settings.members_ou)
        self.assertEqual(user.name.givenName, "John")
        self.assertEqual(user.name.familyName, "van der Doe")

        valid_eid = False
        for eid in user.external_ids:
            if eid.type == "organization" and eid.value == member.pk:
                valid_eid = True
        self.assertTrue(valid_eid)

        # Creation fails
        self._service._generate_username = Mock(return_value=None)
        self.assertIsNone(self._service._create_user_for_member(member, [], clear_cache=False))
        self._service.invalidate_cache.assert_not_called()

    def test_bulk_add(self):
        """Tests adding members in bulk"""
        self._gservice_mock.users.return_value = []
        self._service.invalidate_cache = Mock()
        members = [
            Member.objects.create(email="1@example.com"),
            Member.objects.create(email="2@example.com"),
            Member.objects.create(email="3@example.com"),
        ]

        # Cache should only be cleared once, after all members have been added
        res = self._service.bulk_create_users_for_members(members)
        self._service.invalidate_cache.assert_called_once()
        self.assertEqual(len(res), 3)

        self._service.invalidate_cache.reset_mock()
        self._service._create_user_for_member = Mock(return_value=None)
        res = self._service.bulk_create_users_for_members(members)
        self._service.invalidate_cache.assert_not_called()
        self.assertListEqual(res, [])
