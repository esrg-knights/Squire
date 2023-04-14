from typing import List
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase, override_settings
from unittest.mock import Mock, PropertyMock, patch, ANY

from committees.models import AssociationGroup
from mailcow_integration.api.interface.alias import MailcowAlias
from mailcow_integration.api.interface.mailbox import MailcowMailbox
from mailcow_integration.squire_mailcow import AliasCategory, SquireMailcowManager
from mailcow_integration.admin_status.views import AliasStatus, MailcowStatusView
from membership_file.models import Member

User = get_user_model()

##################################################################################
# Test cases for Squire's Mailcow Status View
# @since 08 APR 2023
##################################################################################

class MailcowStatusViewTests(TestCase):
    """ General class for testing the status view helper methods """
    def setUp(self):
        self.request = RequestFactory().get('/status')
        self.view = MailcowStatusView()
        self.view.setup(self.request)
        self.view.mailcow_manager = SquireMailcowManager(mailcow_host="example.com", mailcow_api_key="fake_key")

class MailcowAliasStatusTests(MailcowStatusViewTests):
    """ Tests the MailcowStatusView._get_alias_status """
    def setUp(self):
        super().setUp()

        self.user1 = User.objects.create(username="User 1", email="user1@example.com")
        self.user2 = User.objects.create(username="User 2", email="user2@example.com")
        self.user3 = User.objects.create(username="User 3", email="user3@example.com")

    @override_settings(
        MEMBER_ALIASES={
            "foo@example.com": {},
        },
        COMMITTEE_CONFIGS={
            'global_addresses': ["bar@example.com"]
        }
    )
    def test_alias_status_reserved(self):
        """ Tests for RESERVED aliases """
        # Alias is reserved (for a member alias)
        status, alias, mailbox = self.view._get_alias_status("foo@example.com", User.objects.none(), AliasCategory.GLOBAL_COMMITTEE, [], [], "")
        self.assertEqual(status, AliasStatus.RESERVED)
        self.assertIsNone(alias)
        self.assertIsNone(mailbox)

        # Alias is reserved (for a global committee alias)
        status, alias, mailbox = self.view._get_alias_status("bar@example.com", User.objects.none(), AliasCategory.COMMITTEE, [], [], "")
        self.assertEqual(status, AliasStatus.RESERVED)
        self.assertIsNone(alias)
        self.assertIsNone(mailbox)


    def test_alias_status_mailbox(self):
        """ Tests for MAILBOX aliases """
        mailboxes = [MailcowMailbox("mailbox@example.com", "Mailbox 1")]

        # Alias is a mailbox
        status, alias, mailbox = self.view._get_alias_status("mailbox@example.com", User.objects.none(), AliasCategory.COMMITTEE, [], mailboxes, "")
        self.assertEqual(status, AliasStatus.MAILBOX)
        self.assertIsNone(alias)
        self.assertIsInstance(mailbox, MailcowMailbox)
        self.assertEqual(mailbox, mailboxes[0])

    def test_alias_status_missing(self):
        """ Tests for MISSING aliases """
        # Alias is a mailbox
        status, alias, mailbox = self.view._get_alias_status("foo@example.com", User.objects.none(), AliasCategory.COMMITTEE, [], [], "")
        self.assertEqual(status, AliasStatus.MISSING)
        self.assertIsNone(alias)
        self.assertIsNone(mailbox)

    def test_alias_status_no_comment(self):
        """ Tests for NOT_MANAGED_BY_SQUIRE aliases """
        aliases = [MailcowAlias("foo@example.com", [], 99, public_comment="Foo!")]
        # Alias is not managed by Squire
        status, alias, mailbox = self.view._get_alias_status("foo@example.com", User.objects.none(), AliasCategory.COMMITTEE, aliases, [], "Bar!")
        self.assertEqual(status, AliasStatus.NOT_MANAGED_BY_SQUIRE)
        self.assertIsInstance(alias, MailcowAlias)
        self.assertEqual(alias, aliases[0])
        self.assertIsNone(mailbox)

    def test_alias_status_valid(self):
        """ Tests for VALID aliases """
        aliases = [MailcowAlias("foo@example.com", [self.user1.email, self.user2.email, self.user3.email], 99, public_comment="Foo!")]
        # Alias is up-to-date (no archive)
        status, alias, mailbox = self.view._get_alias_status("foo@example.com", User.objects.all(), AliasCategory.COMMITTEE, aliases, [], "Foo!")
        self.assertEqual(status, AliasStatus.VALID)
        self.assertIsInstance(alias, MailcowAlias)
        self.assertEqual(alias, aliases[0])
        self.assertIsNone(mailbox)

        # Alias is up-to-date (preprended archive)
        with override_settings(COMMITTEE_CONFIGS={'archive_addresses': ["archief@example.com"], 'global_addresses': []}):
            aliases[0].goto = ["archief@example.com"] + aliases[0].goto
            status, alias, mailbox = self.view._get_alias_status("foo@example.com", User.objects.all(), AliasCategory.COMMITTEE, aliases, [], "Foo!")
            self.assertEqual(status, AliasStatus.VALID)
            self.assertIsInstance(alias, MailcowAlias)
            self.assertEqual(alias, aliases[0])
            self.assertIsNone(mailbox)

        # Alias is up-to-date (Ignores committee emails)
        self.view._committee_addresses = [self.user2.email]
        aliases[0].goto = [self.user1.email, self.user3.email]
        status, alias, mailbox = self.view._get_alias_status("foo@example.com", User.objects.all(), AliasCategory.COMMITTEE, aliases, [], "Foo!")
        self.assertEqual(status, AliasStatus.VALID)
        self.assertIsInstance(alias, MailcowAlias)
        self.assertEqual(alias, aliases[0])
        self.assertIsNone(mailbox)

    def test_alias_status_outdated(self):
        """ Tests for OUTDATED aliases """
        aliases = [MailcowAlias("foo@example.com", [self.user1.email, self.user3.email, self.user2.email], 99, public_comment="Foo!")]
        # Alias is outdated (different order)
        status, alias, mailbox = self.view._get_alias_status("foo@example.com", User.objects.all(), AliasCategory.COMMITTEE, aliases, [], "Foo!")
        self.assertEqual(status, AliasStatus.OUTDATED)
        self.assertIsInstance(alias, MailcowAlias)
        self.assertEqual(alias, aliases[0])
        self.assertIsNone(mailbox)

        # Alias is outdated (archive missing)
        with override_settings(COMMITTEE_CONFIGS={'archive_addresses': ["archief@example.com"], 'global_addresses': []}):
            aliases[0].goto = [self.user1.email, self.user2.email, self.user3.email]
            status, alias, mailbox = self.view._get_alias_status("foo@example.com", User.objects.all(), AliasCategory.COMMITTEE, aliases, [], "Foo!")
            self.assertEqual(status, AliasStatus.OUTDATED)
            self.assertIsInstance(alias, MailcowAlias)
            self.assertEqual(alias, aliases[0])
            self.assertIsNone(mailbox)

        # Alias is outdated (Includes committee email)
        self.view._committee_addresses = [self.user2.email]
        aliases[0].goto = [self.user1.email, self.user2.email, self.user3.email]
        status, alias, mailbox = self.view._get_alias_status("foo@example.com", User.objects.all(), AliasCategory.COMMITTEE, aliases, [], "Foo!")
        self.assertEqual(status, AliasStatus.OUTDATED)
        self.assertIsInstance(alias, MailcowAlias)
        self.assertEqual(alias, aliases[0])
        self.assertIsNone(mailbox)

class MailcowSubscriberInfosTests(MailcowStatusViewTests):
    """ Tests the MailcowStatusView._get_subscriberinfos_by_status """
    def test_infos_not_managed(self):
        """ Tests subscriberinfos when subscribers are not managed by Squire """
        alias = MailcowAlias("foo@example.com", goto=["a@example.com", "b@example.com"])
        subinfos = self.view._get_subscriberinfos_by_status(AliasStatus.NOT_MANAGED_BY_SQUIRE, User.objects.none(), alias, AliasCategory.MEMBER)
        self.assertIn({'name': "a@example.com", 'invalid': False}, subinfos)
        self.assertIn({'name': "b@example.com", 'invalid': False}, subinfos)
        self.assertEqual(len(subinfos), 2)

    def test_infos_no_subs(self):
        """ Tests subscriberinfos when there should be no subscribers """
        # Mailbox
        subinfos = self.view._get_subscriberinfos_by_status(AliasStatus.MAILBOX, User.objects.none(), None, AliasCategory.MEMBER)
        self.assertFalse(subinfos)

        # Reserved for another alias
        subinfos = self.view._get_subscriberinfos_by_status(AliasStatus.RESERVED, User.objects.none(), None, AliasCategory.MEMBER)
        self.assertFalse(subinfos)

    def test_infos_valid(self):
        """ Tests subscriberinfos when subscribers are Members """
        # Member subscribers
        self.view.mailcow_manager.BLOCKLISTED_EMAIL_ADDRESSES = ["foo@example.com"]
        Member.objects.create(first_name='Foo', last_name="Oof", legal_name="Foo Oof", email="foo@example.com")
        Member.objects.create(first_name='Bar', last_name="Rab", legal_name="Bar Rab", email="bar@example.com")
        subinfos = self.view._get_subscriberinfos_by_status(AliasStatus.VALID, Member.objects.all(), None, AliasCategory.MEMBER)
        self.assertEqual(len(subinfos), 2)
        # Blocklisted email is invalid
        # Data is sorted by name
        self.assertEqual(subinfos[0], {'name': "Bar Rab &mdash; bar@example.com", 'invalid': False})
        self.assertEqual(subinfos[1], {'name': "Foo Oof &mdash; foo@example.com", 'invalid': True})

        # Committee Subscribers
        AssociationGroup.objects.create(site_group=Group.objects.create(name="Boardgamers"),
            type=AssociationGroup.COMMITTEE, contact_email="bg@example.com")
        subinfos = self.view._get_subscriberinfos_by_status(AliasStatus.VALID, AssociationGroup.objects.all(), None, AliasCategory.GLOBAL_COMMITTEE)
        self.assertEqual(len(subinfos), 1)
        self.assertEqual(subinfos[0], {'name': "Boardgamers (Committee) &mdash; bg@example.com", 'invalid': False})

class MailcowStatusExposureTests(MailcowStatusViewTests):
    """ Tests exposure route detection """
    def setUp(self):
        super().setUp()
        self.member_aliases = {
            "foo@example.com": {
                "internal": True,
            },
            "internal@example.com": {
                "internal": True
            },
            "public@example.com": {
                "internal": False
            }
        }

    def test_exposed_direct(self):
        """ Tests if exposure routes are found when there is one direct exposure """
        aliases = [MailcowAlias("exposer@example.com", ["baz@example.com", "foo@example.com", "abc@example.com"])]

        exposure_routes = self.view._get_alias_exposure_routes("foo@example.com", aliases, [], self.member_aliases)
        self.assertListEqual(exposure_routes, [["exposer@example.com"]])

    def test_exposed_direct_multiple(self):
        """ Tests if exposure routes are found when there are multiple direct exposures """
        aliases = [
            MailcowAlias("exposer1@example.com", ["baz@example.com", "foo@example.com", "abc@example.com"]),
            MailcowAlias("exposer0@example.com", ["foo@example.com", "abc@example.com"]),
            MailcowAlias("exposer2@example.com", ["baz@example.com", "foo@example.com"])
        ]

        exposure_routes = self.view._get_alias_exposure_routes("foo@example.com", aliases, [], self.member_aliases)
        # Exposed addresses are sorted alphabetically
        self.assertListEqual(exposure_routes, [
            ["exposer0@example.com"],
            ["exposer1@example.com"],
            ["exposer2@example.com"]
        ])

    def test_member_alias_exposure(self):
        """ Tests if exposure routes are found depending on the internal-status of an alias """
        aliases = [
            MailcowAlias("internal@example.com", ["baz@example.com", "foo@example.com", "abc@example.com"]),
            MailcowAlias("public@example.com", ["baz@example.com", "foo@example.com", "abc@example.com"]),
        ]

        exposure_routes = self.view._get_alias_exposure_routes("foo@example.com", aliases, [], self.member_aliases)
        # Internal alias cannot expose another internal alias
        self.assertNotIn(["internal@example.com"], exposure_routes)
        # Public alias should expose an internal alias
        self.assertListEqual(exposure_routes, [["public@example.com"]])

    def test_exposed_indirect(self):
        """ Tests if exposure routes are found when there is one indirect exposure """
        aliases = [
            MailcowAlias("internal@example.com", ["baz@example.com", "foo@example.com", "abc@example.com"]),
            MailcowAlias("exposed@example.com", ["baz@example.com", "internal@example.com", "abc@example.com"]),
        ]

        exposure_routes = self.view._get_alias_exposure_routes("foo@example.com", aliases, [], self.member_aliases)
        # Address exposed via [exposed@example.com -> internal@example.com -> foo@example.com]
        self.assertListEqual(exposure_routes, [["exposed@example.com", "internal@example.com"]])

        # Test a very indirect exposure route
        expected_exposure_route = []
        aliases = []
        for i in range(10):
            expected_exposure_route.append(f"addr{i}@example.com")
            # Note: addr0@example.com is public
            self.member_aliases[f"addr{i+1}@example.com"] = {"internal": True}
            aliases.append(MailcowAlias(f"addr{i}@example.com", [f"addr{i+1}@example.com"]))
        aliases.append(MailcowAlias("addr10@example.com", ["foo@example.com"]))
        expected_exposure_route.append(f"addr10@example.com")
        exposure_routes = self.view._get_alias_exposure_routes("foo@example.com", aliases, [], self.member_aliases)
        # Exposed via [addr0@example.com -> addr1@example.com -> addr2@example.com -> addr3@example.com
        #   -> addr4@example.com -> addr5@example.com -> addr6@example.com -> addr7@example.com
        #   -> addr8@example.com -> addr9@example.com -> addr10@example.com -> foo@example.com]
        self.assertListEqual(exposure_routes, [expected_exposure_route])

    def test_exposed_indirect_multiple(self):
        """ Tests if exposure routes are found when there is one indirect exposure """
        aliases = [
            MailcowAlias("exposed2@example.com", ["baz@example.com", "internal@example.com", "abc@example.com"]),
            MailcowAlias("internal@example.com", ["baz@example.com", "foo@example.com", "abc@example.com"]),
            MailcowAlias("exposed1@example.com", ["baz@example.com", "internal@example.com", "abc@example.com"]),
        ]

        exposure_routes = self.view._get_alias_exposure_routes("foo@example.com", aliases, [], self.member_aliases)
        # Address exposed via [exposed@example.com -> internal@example.com -> foo@example.com]
        self.assertListEqual(exposure_routes, [
            ["exposed1@example.com", "internal@example.com"],
            ["exposed2@example.com", "internal@example.com"]
        ])
