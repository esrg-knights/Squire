from unittest.mock import Mock

from django.test import TestCase

from committees.email import MemberMailingListAliasSettings, SquireEmailManager
from committees.models import AssociationGroup
from gworkspace_integration.api.client import GoogleWorkspaceSettings
from gworkspace_integration.api.formats.groups import WorkspaceGroup
from gworkspace_integration.api.formats.users import WorkspaceUser
from gworkspace_integration.workspace_manager.planner.proxy import (
    WorkspaceGroupMemberCommittee,
    WorkspaceGroupMemberProxy,
    WorkspaceGroupMemberSqMember,
    WorkspaceGroupMemberWGroup,
    WorkspaceGroupMemberWUser,
    WorkspaceGroupProxy,
)
from membership_file.models import Member


class ProxyTestCase(TestCase):
    """Tests several proxies"""

    def setUp(self):
        super().setUp()
        self._settings = GoogleWorkspaceSettings(
            "/my_token", "example.com", ["voorbeeld.nl"], "12345", "/Test", "admin@example.com", []
        )

    def test_mailing_list_proxy(self):
        """WorkspaceGroupProxy creation methods"""
        # We're not interested in the setup of most of the implementation specifics. Just test the bare minimum
        members = [
            Member.objects.create(email="member1@example.com"),
            Member.objects.create(email="member2@example.com"),
            Member.objects.create(email="member3@example.com"),
        ]
        committee = AssociationGroup.objects.create(name="Comm", contact_email="foo@example.com")
        for m in members:
            committee.members.add(m)
        res = WorkspaceGroupProxy.from_committee(committee)
        self.assertEqual(res.email, committee.contact_email)
        self.assertEqual(len(res.members), 3)
        self.assertIsInstance(res.members[0], WorkspaceGroupMemberProxy)

        SquireEmailManager.get_subscribed_members = Mock(return_value=members)
        res = WorkspaceGroupProxy.from_member_mailing_list(
            ("baz@example.com", MemberMailingListAliasSettings("T", "D"))
        )
        self.assertEqual(res.email, "baz@example.com")
        SquireEmailManager.get_subscribed_members.assert_called_once()
        self.assertEqual(len(res.members), 3)
        self.assertIsInstance(res.members[0], WorkspaceGroupMemberProxy)

        SquireEmailManager.get_active_committees = Mock(
            return_value=[AssociationGroup(contact_email="com@example.com")]
        )
        res = WorkspaceGroupProxy.from_committee_mailing_list("bar@example.com")
        SquireEmailManager.get_active_committees.assert_called_once()
        self.assertEqual(res.email, "bar@example.com")
        self.assertIsInstance(res.members[0], WorkspaceGroupMemberProxy)

    def test_wgroup_member_proxy_squire_member(self):
        """WorkspaceGroupMemberProxy for Squire Members"""
        member = Member(email="bar@example.com")
        res = WorkspaceGroupMemberSqMember.from_proxy(member)
        self.assertEqual(res.email, member.email)

        self.assertFalse(res.is_manual(self._settings))
        self.assertFalse(res.is_valid(self._settings))
        res.email = "bar@voorbeeld.nl"
        self.assertFalse(res.is_valid(self._settings))
        res.email = self._settings.directory_admin_username
        self.assertTrue(res.is_valid(self._settings))
        res.email = "bar@gmail.com"
        self.assertTrue(res.is_valid(self._settings))

    def test_wgroup_member_proxy_squire_committeee(self):
        """WorkspaceGroupMemberProxy for Squire Committees"""
        committee = AssociationGroup(name="Comm", contact_email="foo@gmail.com")
        res = WorkspaceGroupMemberCommittee.from_proxy(committee)
        self.assertEqual(res.email, committee.contact_email)

        self.assertFalse(res.is_valid(self._settings))
        self.assertFalse(res.is_manual(self._settings))
        res.email = "foo@example.com"
        self.assertTrue(res.is_valid(self._settings))
        res.email = "foo@voorbeeld.nl"
        self.assertTrue(res.is_valid(self._settings))

    def test_wgroup_member_proxy_gworkspace_group(self):
        """WorkspaceGroupMemberProxy for Workspace Groups"""
        group = WorkspaceGroup(email="foo@example.com")
        res = WorkspaceGroupMemberWGroup.from_proxy(group)
        self.assertEqual(res.email, group.email)

        self.assertTrue(res.is_valid(self._settings))
        self.assertFalse(res.is_manual(self._settings))

    def test_wgroup_member_proxy_gworkspace_user(self):
        """WorkspaceGroupMemberProxy for Workspace Users"""
        user = WorkspaceUser(primaryEmail="foo@example.com", orgUnitPath="/Test")
        res = WorkspaceGroupMemberWUser.from_proxy(user)
        self.assertEqual(res.email, user.primaryEmail)

        self.assertTrue(res.is_valid(self._settings))
        self.assertFalse(res.is_manual(self._settings))
        user.orgUnitPath = "/My_Manual_OU"
        self.assertTrue(res.is_manual(self._settings))
        res.email = self._settings.directory_admin_username
        self.assertFalse(res.is_manual(self._settings))
