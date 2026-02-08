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
from gworkspace_integration.workspace_manager.planner.proxy import WorkspaceGroupMemberProxy, WorkspaceGroupMemberWUser
from gworkspace_integration.workspace_manager.planner.sync import (
    SquireWorkspaceGroupSyncHelper,
    WorkspaceGroupMemberSync,
    WorkspaceGroupMemberSyncStatus,
)


class WorkspaceGroupMemberProxyTestInvalid(WorkspaceGroupMemberProxy):
    """Helper class to test invalid proxies"""

    def is_valid(self, settings):
        return False


class WorkspaceGroupMemberProxyTestManual(WorkspaceGroupMemberProxy):
    """Helper class to test manual proxies"""

    def is_manual(self, settings):
        return True


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
        self.assertEqual(sync.name, "<Invalid Group Member>")

        sync.wmember_proxy = WorkspaceGroupMemberWUser.from_proxy(WorkspaceUser(name=WorkspaceUserName("fullname")))
        self.assertEqual(sync.name, "fullname")

        # prioritize member name
        sync.sqmember_proxy = self.member_proxy
        self.assertEqual(sync.name, "proxyname")

    def test_sync_add(self):
        """Tests sync status add"""
        res = self.planner.get_sync([(self.members[0], self.member_proxy)])
        res = list(self.planner.calc_base_sync([], res))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_ADD)
        self.assertEqual(res[0].wgroup_member, self.members[0])
        self.assertIsNone(res[0].wmember_proxy)
        self.assertEqual(res[0].sqmember_proxy, self.member_proxy)

    def test_sync_remove(self):
        """Tests sync status remove"""
        res = self.planner.get_sync([])
        res = list(self.planner.calc_base_sync([self.members[0]], res))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_REMOVE)
        self.assertEqual(res[0].wgroup_member, self.members[0])
        self.assertIsNone(res[0].wmember_proxy)
        self.assertIsNone(res[0].sqmember_proxy)

    def test_sync_update(self):
        """Tests sync status update"""

        self.members[1].role = WorkspaceGroupMemberRole.OWNER
        self.members[1].id = 4
        res = self.planner.get_sync([(self.members[0], self.member_proxy)])
        res = list(self.planner.calc_base_sync([self.members[1]], res))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, WorkspaceGroupMemberSyncStatus.SYNC_SHOULD_UPDATE)
        self.assertEqual(res[0].wgroup_member, self.members[0])
        self.assertEqual(res[0].wgroup_member.id, 4)  # id is updated based on the current member
        self.assertIsNone(res[0].wmember_proxy)
        self.assertEqual(res[0].sqmember_proxy, self.member_proxy)

    def test_sync_up_to_date(self):
        """Tests sync status upt-to-date"""
        res = self.planner.get_sync([(self.members[0], self.member_proxy)])
        res = list(self.planner.calc_base_sync([self.members[1]], res))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, WorkspaceGroupMemberSyncStatus.SYNC_UP_TO_DATE)
        self.assertEqual(res[0].wgroup_member, self.members[0])
        self.assertIsNone(res[0].wmember_proxy)
        self.assertEqual(res[0].sqmember_proxy, self.member_proxy)

    def test_verify_sync(self):
        """Tests sync status INVALID and NOTOUCH"""
        sync = WorkspaceGroupMemberSync(self.members[0], WorkspaceGroupMemberSyncStatus.SYNC_UP_TO_DATE)

        # Status untouched
        res = list(self.planner.verify_sync([sync]))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, WorkspaceGroupMemberSyncStatus.SYNC_UP_TO_DATE)

        # Status Invalid
        sync.sqmember_proxy = WorkspaceGroupMemberProxyTestInvalid(None, "name", "email")
        res = list(self.planner.verify_sync([sync]))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, WorkspaceGroupMemberSyncStatus.SYNC_INVALID)

        # Status Manual
        sync.wmember_proxy = WorkspaceGroupMemberProxyTestManual(None, "name", "email")
        res = list(self.planner.verify_sync([sync]))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, WorkspaceGroupMemberSyncStatus.SYNC_NOTOUCH)
