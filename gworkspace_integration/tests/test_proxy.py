from unittest.mock import Mock

from django.test import TestCase

from committees.email import MemberMailingListAliasSettings, SquireEmailManager
from committees.models import AssociationGroup
from gworkspace_integration.workspace_manager.planner.proxy import MailingListMemberProxy, MailingListProxy
from membership_file.models import Member


class ProxyTestCase(TestCase):
    """Tests several proxies"""

    def setUp(self):
        super().setUp()

    def test_mailing_list_proxy(self):
        """MailingListProxy creation methods"""
        # We're not interested in the setup of most of the implementation specifics. Just test the bare minimum
        members = [
            Member.objects.create(email="member1@example.com"),
            Member.objects.create(email="member2@example.com"),
            Member.objects.create(email="member3@example.com"),
        ]
        committee = AssociationGroup.objects.create(name="Comm", contact_email="foo@example.com")
        for m in members:
            committee.members.add(m)
        res = MailingListProxy.from_committee(committee)
        self.assertEqual(res.email, committee.contact_email)
        self.assertEqual(len(res.members), 3)
        self.assertIsInstance(res.members[0], MailingListMemberProxy)

        SquireEmailManager.get_subscribed_members = Mock(return_value=members)
        res = MailingListProxy.from_member_mailing_list(("baz@example.com", MemberMailingListAliasSettings("T", "D")))
        self.assertEqual(res.email, "baz@example.com")
        SquireEmailManager.get_subscribed_members.assert_called_once()
        self.assertEqual(len(res.members), 3)
        self.assertIsInstance(res.members[0], MailingListMemberProxy)

        SquireEmailManager.get_active_committees = Mock(
            return_value=[AssociationGroup(contact_email="com@example.com")]
        )
        res = MailingListProxy.from_committee_mailing_list("bar@example.com")
        SquireEmailManager.get_active_committees.assert_called_once()
        self.assertEqual(res.email, "bar@example.com")
        self.assertIsInstance(res.members[0], MailingListMemberProxy)

    def test_mailing_list_member_proxy(self):
        """MailingListMemberProxy creation methods"""
        # We're not interested in the setup of implementation specifics
        committee = AssociationGroup(name="Comm", contact_email="foo@example.com")
        res = MailingListMemberProxy.from_committee(committee)
        self.assertEqual(res.email, committee.contact_email)

        member = Member(email="bar@example.com")
        res = MailingListMemberProxy.from_member(member)
        self.assertEqual(res.email, member.email)
