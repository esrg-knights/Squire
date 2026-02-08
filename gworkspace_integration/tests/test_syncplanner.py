from unittest.mock import Mock

from django.test import TestCase

from gworkspace_integration.api.client import GoogleWorkspaceSettings
from gworkspace_integration.api.formats.groups import (
    WorkspaceGroupMember,
    WorkspaceGroupMemberDeliverySettings,
    WorkspaceGroupMemberRole,
    WorkspaceGroupMemberType,
)
from gworkspace_integration.api.formats.users import WorkspaceUser, WorkspaceUserName
from gworkspace_integration.workspace_manager.planner.proxy import WorkspaceGroupMemberProxy
from gworkspace_integration.workspace_manager.planner.sync import (
    SquireWorkspaceGroupSyncHelper,
    WorkspaceGroupMemberSync,
    WorkspaceGroupMemberSyncStatus,
)


class SyncHelperTestCase(TestCase):
    """Tests for sync calculations"""

    def setUp(self):
        super().setUp()
        settings = GoogleWorkspaceSettings(
            "/my_token", "email.com", ["voorbeeld.nl", "test.com"], "12345", "/Test", "admin@email.com", []
        )
        self.planner = SquireWorkspaceGroupSyncHelper(settings)

        self.members = [
            WorkspaceGroupMember(
                kind="mykind",
                email=f"member@example.com",
                role=WorkspaceGroupMemberRole.MEMBER,
                type=WorkspaceGroupMemberType.USER,
                delivery_settings=WorkspaceGroupMemberDeliverySettings.ALL_MAIL,
            )
            for x in range(2)
        ]

        self.member_proxy = WorkspaceGroupMemberProxy(5, "proxyname", "test@example.com")

    def test_name(self):
        """Tests name method of a sync"""
        sync = WorkspaceGroupMemberSync(self.members[0], WorkspaceGroupMemberSyncStatus.SYNC_UP_TO_DATE, None, None)
        self.assertEqual(sync.name, "")

        sync.wmember_proxy = WorkspaceUser(name=WorkspaceUserName("fullname"))
        self.assertEqual(sync.name, "fullname")

        # prioritize member name
        sync.sqmember_proxy = self.member_proxy
        self.assertEqual(sync.name, "proxyname")

    def test_valid_email(self):
        """Tests email validity"""
        self.assertFalse(self.planner.is_email_valid_for_sync("foo@email.com"))
        self.assertFalse(self.planner.is_email_valid_for_sync("foo@voorbeeld.nl"))
        self.assertFalse(self.planner.is_email_valid_for_sync("foo@test.com"))
        self.assertTrue(self.planner.is_email_valid_for_sync("foo@example.com"))
        self.assertTrue(self.planner.is_email_valid_for_sync("admin@email.com"))

        # Give INVALID status
        self.members[0].email = "test@voorbeeld.nl"
        res = self.planner.calc_base_sync([], [(self.members[0], self.member_proxy)])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, WorkspaceGroupMemberSyncStatus.SYNC_INVALID)
        self.assertEqual(res[0].wgroup_member, self.members[0])
        self.assertIsNone(res[0].workspace_user)
        self.assertEqual(res[0].member_proxy, self.member_proxy)

    def test_sync_add(self):
        """Tests sync status add"""
        res = self.planner.calc_base_sync([], [(self.members[0], self.member_proxy)])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_ADD)
        self.assertEqual(res[0].wgroup_member, self.members[0])
        self.assertIsNone(res[0].workspace_user)
        self.assertEqual(res[0].member_proxy, self.member_proxy)

    def test_sync_remove(self):
        """Tests sync status remove"""
        res = self.planner.calc_base_sync([self.members[0]], [])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_REMOVE)
        self.assertEqual(res[0].wgroup_member, self.members[0])
        self.assertIsNone(res[0].workspace_user)
        self.assertIsNone(res[0].member_proxy)

    def test_sync_update(self):
        """Tests sync status update"""

        self.members[1].role = WorkspaceGroupMemberRole.OWNER
        self.members[1].id = 4
        res = self.planner.calc_base_sync([self.members[1]], [(self.members[0], self.member_proxy)])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_UPDATE)
        self.assertEqual(res[0].wgroup_member, self.members[0])
        self.assertEqual(res[0].wgroup_member.id, 4)  # id is updated based on the current member
        self.assertIsNone(res[0].workspace_user)
        self.assertEqual(res[0].member_proxy, self.member_proxy)

    def test_sync_up_to_date(self):
        """Tests sync status upt-to-date"""
        res = self.planner.calc_base_sync([self.members[1]], [(self.members[0], self.member_proxy)])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, WorkspaceGroupMemberSyncStatus.SYNC_UP_TO_DATE)
        self.assertEqual(res[0].wgroup_member, self.members[0])
        self.assertIsNone(res[0].workspace_user)
        self.assertEqual(res[0].member_proxy, self.member_proxy)
