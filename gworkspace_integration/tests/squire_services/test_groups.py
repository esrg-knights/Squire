from unittest.mock import Mock

from django.test import TestCase

from committees.models import AssociationGroup
from gworkspace_integration.api.client import GoogleWorkspaceSettings
from gworkspace_integration.api.formats.groups import WorkspaceGroup, WorkspaceGroupMember, WorkspaceGroupMemberRole
from gworkspace_integration.workspace_manager.planner.proxy import MailingListMemberProxy, MailingListProxy
from gworkspace_integration.workspace_manager.services.groups import SquireWorkspaceGroupService


class SquireGroupServiceTestCase(TestCase):
    """Tests groups service"""

    def setUp(self):
        super().setUp()
        settings = GoogleWorkspaceSettings(
            "/my_token", "example.com", ["voorbeeld.nl"], "12345", "/Test", "admin@example.com", []
        )
        self._gservice_mock = Mock()
        self._sqservice_user_mock = Mock()

        self._service = SquireWorkspaceGroupService(self._gservice_mock, settings, self._sqservice_user_mock)
        # We're not interested in the specifics of caching, just call the function directly!
        self._cache_fetch = self._service.fetch_with_lock = Mock(side_effect=lambda api_fn, *args, **kwargs: api_fn())

    def test_groups(self):
        """Tests fetching groups"""
        self._gservice_mock.groups.return_value = ["5"]

        res = self._service.groups(True)
        self._cache_fetch.assert_not_called()
        self._gservice_mock.groups.assert_called_once()
        self.assertListEqual(res, ["5"])

        self._gservice_mock.reset_mock()
        self._service.groups(False)
        self._cache_fetch.assert_called_once()
        self._gservice_mock.groups.assert_called_once()
        self.assertListEqual(res, ["5"])

    def test_group_members(self):
        """Tests fetching group members"""
        self._gservice_mock.group_members.return_value = ["5"]

        res = self._service.group_members(WorkspaceGroup(email="test@example.com", id="myid"))
        self._cache_fetch.assert_called_once()
        self._gservice_mock.group_members.assert_called_once_with("myid")
        self.assertListEqual(res, ["5"])

    def test_get_group_committee(self):
        """Tests fetching groups for committees"""
        committee = AssociationGroup(pk=2, name="MyCommittee")
        groups = [
            WorkspaceGroup(id="7"),
            WorkspaceGroup(id="8", aliases=["baz@example.com"]),
            WorkspaceGroup(id="9", aliases=["foo@example.com", "committee-2@example.com", "bar@example.com"]),
        ]
        # Group should be found
        self.assertEqual(self._service.get_group_for_committee(committee, groups).id, "9")
        self.assertIsNone(self._service.get_group_for_committee(committee, []))

    def test_get_committee_group(self):
        """Tests fetching committee for group"""
        # Corresponding committee does not exist
        group = WorkspaceGroup(
            id="7", aliases=["committee-000@example.com", "committee-001@example.com", "bar@example.com"]
        )
        self.assertIsNone(self._service.get_committee_for_group(group))

        # It does now!
        committee = AssociationGroup.objects.create(name="MyCommittee")
        group.aliases[1] = f"committee-{committee.pk}@example.com"
        self.assertEqual(self._service.get_committee_for_group(group), committee.pk)

    def test_misc_defaults(self):
        """Tests various methods that setup defaults. There's no need to test the specific default values; those might change in the future"""
        # Committees to sync
        res = self._service.get_active_committees()
        self.assertEqual(res.model, AssociationGroup)

        # Default Workspace group member based on proxy member
        self.assertIsInstance(
            self._service._get_default_wgroup_member(MailingListMemberProxy(5, "myname", "foo@example.com")),
            WorkspaceGroupMember,
        )

        # Default Workspace group owner
        self.assertIsInstance(
            self._service._get_wgroup_default_owner(),
            WorkspaceGroupMember,
        )

    def test_default_mailinglist_members(self):
        """Tests default mailing list members"""
        mailing_list = MailingListProxy(
            "uuid",
            "name",
            "type",
            "email",
            pk=5,
            members=[
                MailingListMemberProxy(1, "foo", "foo@example.com"),
                MailingListMemberProxy(2, "bar", "bar@example.com"),
            ],
        )

        res = self._service._get_wgroup_members_for_mailinglist(mailing_list)
        has_admin_as_owner = False
        for gmember, proxymember in res:
            if (
                gmember.email == "admin@example.com"
                and gmember.role == WorkspaceGroupMemberRole.OWNER
                and proxymember is None
            ):
                has_admin_as_owner = True

        self.assertTrue(has_admin_as_owner)
        self.assertEqual(len(res), 3)

    def test_mailinglist_group(self):
        """Tests obtaining the Workspace group for a mailing list"""
        groups = [
            WorkspaceGroup(id="7", email="bar@example.com"),
            WorkspaceGroup(id="8", email="foo@example.com"),
            WorkspaceGroup(id="9", email="baz@example.com"),
        ]
        self.assertIsNone(self._service.get_group_for_mailinglist("test@example.com", groups))
        self.assertEqual(self._service.get_group_for_mailinglist("foo@example.com", groups).id, "8")

    def test_sync(self):
        """Tests syncing a committee and a Workspace group"""
        # member_1: already correctly synced (up-to-date)
        member_1 = MailingListMemberProxy(1, "Member 1", "member-1@test.com")
        # owner: should update (role is out of date)
        owner = self._service._get_wgroup_default_owner()
        owner.role = WorkspaceGroupMemberRole.MANAGER

        gmember_1 = self._service._get_default_wgroup_member(member_1)
        gmember_1.id = "gid"
        self._gservice_mock.group_members.return_value = [
            gmember_1,
            # member 3: only in workspace (should remove)
            WorkspaceGroupMember("admin#directory#member", "member-3@test.com", id="gid-3"),
            owner,
        ]

        mailing_list = mailing_list = MailingListProxy(
            "uuid",
            "name",
            "type",
            "email",
            pk=5,
            members=[
                # member 2: only present in committee (should add)
                MailingListMemberProxy(2, "Member 2", "member-2@test.com"),
                member_1,
            ],
        )

        group = WorkspaceGroup(id="9", email="group@example.com")
        self._service.bulk_sync_group_members(mailing_list, group)

        self._gservice_mock.bulk_change_group_members.assert_called_once()
        groupKey, should_update, should_add, should_remove = self._gservice_mock.bulk_change_group_members.call_args[0]
        self.assertEqual(groupKey, "9")
        res = f"should_update={should_update}, should_add={should_add}, should_remove={should_remove}"
        # Owner updated
        self.assertEqual(len(should_update), 1, f"Owner should be updated; {res}")
        res_owner: WorkspaceGroupMember = should_update[0]
        self.assertEqual(res_owner.email, owner.email, f"Owner should be updated! {res}")
        self.assertEqual(res_owner.role, WorkspaceGroupMemberRole.OWNER, f"Owner should have OWNER role! {res_owner}")
        # Member 2 added
        self.assertEqual(len(should_add), 1, f"Member 2 should be added; {res}")
        res_member2: WorkspaceGroupMember = should_add[0]
        self.assertEqual(res_member2.email, "member-2@test.com", f"Member 2 should be added! {res}")
        # Member 3 removed
        self.assertEqual(len(should_remove), 1, f"Member 3 should be removed; {res}")
        res_member3: WorkspaceGroupMember = should_remove[0]
        self.assertEqual(res_member3.email, "member-3@test.com", f"Member 3 should be removed! {res}")

        # No need to test SYNC_INVALID; we're not interested in how the syncPlanner sets it
