from unittest.mock import Mock, ANY
from django.test import TestCase

from core.tests.util import suppress_warnings
from gworkspace_integration.api.formats.groups import (
    WorkspaceGroup,
    WorkspaceGroupMember,
    WorkspaceGroupMemberDeliverySettings,
    WorkspaceGroupMemberRole,
    WorkspaceGroupMemberType,
)
from gworkspace_integration.api.formats.users import WorkspaceUser
from gworkspace_integration.api.services.directory_service import DirectoryService
from gworkspace_integration.tests.util import GoogleServiceTestMixin


class GoogleAPIDirectoryServiceTestCase(GoogleServiceTestMixin[DirectoryService], TestCase):
    """Tests for Google Workspace's Directory Service"""

    service_class = DirectoryService

    @suppress_warnings(logger_name="gworkspace_api")
    def test_get_users(self):
        """Tests whether users can be obtained, possibly paginated"""
        mock_execute: Mock = self._google_service.users.return_value.list.return_value.execute
        mock_execute.side_effect = [
            {"users": [{"id": "0"}], "nextPageToken": "next_token"},
            {"users": [{"id": "1"}]},
        ]
        users = list(self.service.users())

        self.assertEqual(mock_execute.call_count, 2)
        self.assertEqual(len(users), 2)
        for i in range(2):
            self.assertIsInstance(users[i], WorkspaceUser)
            self.assertEqual(users[i].id, str(i))

    def test_create_user(self):
        """Tests user creation"""
        mock_execute: Mock = self._google_service.users.return_value.insert.return_value.execute

        # Attempting to add a user with a domain not in the settings file should raise an error
        with self.assertRaises(ValueError):
            self.service.add_user(WorkspaceUser(id="0", primaryEmail="foo@nonconfigureddomain.com"))
        mock_execute.assert_not_called()

        # Valid domain
        self.service.add_user(WorkspaceUser(id="0", primaryEmail="foo@example.com"))
        mock_execute.assert_called_once()

    # --------
    # GROUPS
    # --------
    @suppress_warnings(logger_name="gworkspace_api")
    def test_get_groups(self):
        """Tests whether groups can be obtained, possibly paginated"""
        mock_execute: Mock = self._google_service.groups.return_value.list.return_value.execute
        mock_execute.side_effect = [
            {"groups": [{"id": "0"}], "nextPageToken": "next_token"},
            {"groups": [{"id": "1"}]},
        ]
        groups = list(self.service.groups())

        self.assertEqual(mock_execute.call_count, 2)
        self.assertEqual(len(groups), 2)
        for i in range(2):
            self.assertIsInstance(groups[i], WorkspaceGroup)
            self.assertEqual(groups[i].id, str(i))

    @suppress_warnings(logger_name="gworkspace_api")
    def test_get_group_members(self):
        """Tests whether group members can be obtained, possibly paginated"""
        mock_execute: Mock = self._google_service.members.return_value.list.return_value.execute
        mock_execute.side_effect = [
            {"members": [{"id": "0"}], "nextPageToken": "next_token"},
            {"members": [{"id": "1"}]},
        ]
        members = list(self.service.group_members("my_group"))

        self.assertEqual(mock_execute.call_count, 2)
        self.assertEqual(len(members), 2)
        for i in range(2):
            self.assertIsInstance(members[i], WorkspaceGroupMember)
            self.assertEqual(members[i].id, str(i))

    def test_bulk_change_group_members(self):
        """Tests whether bulk syncing group members functions"""
        mock_batch: Mock = self._google_service.new_batch_http_request
        mock_batch_add: Mock = mock_batch.return_value.add
        mock_insert: Mock = self._google_service.members.return_value.insert
        mock_delete: Mock = self._google_service.members.return_value.delete
        mock_patch: Mock = self._google_service.members.return_value.patch

        member_1 = WorkspaceGroupMember(
            kind="mykind",
            email="member1@example.com",
            role=WorkspaceGroupMemberRole.MANAGER,
            type=WorkspaceGroupMemberType.USER,
            delivery_settings=WorkspaceGroupMemberDeliverySettings.DAILY,
            id="m1",
        )
        member_2 = WorkspaceGroupMember(
            kind="mykind",
            email="member2@example.com",
            role=WorkspaceGroupMemberRole.MEMBER,
            type=WorkspaceGroupMemberType.USER,
            delivery_settings=WorkspaceGroupMemberDeliverySettings.ALL_MAIL,
            id="m2",
        )

        # Only adding
        self.service.bulk_change_group_members("my_group", [], [member_1, member_2], [])

        self.assertEqual(mock_insert.call_count, 2)
        _, kwargs = mock_insert.call_args_list[0]
        self.assertEqual(kwargs.get("groupKey", None), "my_group")
        self.assertEqual(kwargs.get("body", {}).get("email", None), "member1@example.com")
        _, kwargs = mock_insert.call_args_list[1]
        self.assertEqual(kwargs.get("groupKey", None), "my_group")
        self.assertEqual(kwargs.get("body", {}).get("email", None), "member2@example.com")
        mock_delete.assert_not_called()
        mock_patch.assert_not_called()
        mock_batch.assert_called_once()
        self.assertEqual(mock_batch_add.call_count, 2)

        mock_batch.reset_mock()
        mock_batch_add.reset_mock()
        mock_insert.reset_mock()
        mock_delete.reset_mock()
        mock_patch.reset_mock()

        # Updating and deleting
        self.service.bulk_change_group_members("my_group", [member_2], [], [member_1])
        mock_insert.assert_not_called()
        mock_patch.assert_called_once()

        _, kwargs = mock_patch.call_args
        self.assertEqual(kwargs.get("groupKey", None), "my_group")
        self.assertEqual(kwargs.get("memberKey", None), "m2")
        self.assertEqual(kwargs.get("body", {}).get("email", None), "member2@example.com")

        mock_delete.assert_called_once()
        _, kwargs = mock_delete.call_args
        self.assertEqual(kwargs.get("groupKey", None), "my_group")
        self.assertEqual(kwargs.get("memberKey", None), "m1")
        self.assertNotIn("body", kwargs)

        self.assertEqual(mock_batch.call_count, 2)
        self.assertEqual(mock_batch_add.call_count, 2)
