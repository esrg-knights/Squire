from typing import List
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils.html import format_html
from unittest.mock import Mock, patch, sentinel, ANY

from committees.models import AssociationGroup
from core.tests.util import suppress_errors
from mailcow_integration.api.exceptions import (
    MailcowAPIAccessDenied,
    MailcowAPIReadWriteAccessDenied,
    MailcowAuthException,
    MailcowException,
)
from mailcow_integration.api.interface.alias import MailcowAlias
from mailcow_integration.api.interface.mailbox import MailcowMailbox
from mailcow_integration.squire_mailcow import AliasCategory, SquireMailcowManager
from mailcow_integration.admin_status.views import AliasInfos, AliasStatus, MailcowStatusView
from membership_file.models import Member

User = get_user_model()

##################################################################################
# Test cases for Squire's Mailcow Status View
# @since 08 APR 2023
##################################################################################


class MailcowStatusViewTests(TestCase):
    """General class for testing the status view helper methods"""

    def setUp(self):
        self.request = RequestFactory().get("/status")
        self.view = MailcowStatusView()
        self.view.setup(self.request)
        self.view.mailcow_manager = SquireMailcowManager(mailcow_host="example.com", mailcow_api_key="fake_key")


class MailcowAliasStatusTests(MailcowStatusViewTests):
    """Tests the MailcowStatusView._get_alias_status"""

    def setUp(self):
        super().setUp()

        self.user1 = User.objects.create(username="User 1", email="user1@example.com")
        self.user2 = User.objects.create(username="User 2", email="user2@example.com")
        self.user3 = User.objects.create(username="User 3", email="user3@example.com")

    @override_settings(
        MEMBER_ALIASES={
            "foo@example.com": {},
        },
        COMMITTEE_CONFIGS={"global_addresses": ["bar@example.com"]},
    )
    def test_alias_status_reserved(self):
        """Tests for RESERVED aliases"""
        # Alias is reserved (for a member alias)
        status, alias, mailbox = self.view._get_alias_status(
            "foo@example.com", User.objects.none(), AliasCategory.GLOBAL_COMMITTEE, [], [], ""
        )
        self.assertEqual(status, AliasStatus.RESERVED)
        self.assertIsNone(alias)
        self.assertIsNone(mailbox)

        # Alias is reserved (for a global committee alias)
        status, alias, mailbox = self.view._get_alias_status(
            "bar@example.com", User.objects.none(), AliasCategory.COMMITTEE, [], [], ""
        )
        self.assertEqual(status, AliasStatus.RESERVED)
        self.assertIsNone(alias)
        self.assertIsNone(mailbox)

    def test_alias_status_mailbox(self):
        """Tests for MAILBOX aliases"""
        mailboxes = [MailcowMailbox("mailbox@example.com", "Mailbox 1")]

        # Alias is a mailbox
        status, alias, mailbox = self.view._get_alias_status(
            "mailbox@example.com", User.objects.none(), AliasCategory.COMMITTEE, [], mailboxes, ""
        )
        self.assertEqual(status, AliasStatus.MAILBOX)
        self.assertIsNone(alias)
        self.assertIsInstance(mailbox, MailcowMailbox)
        self.assertEqual(mailbox, mailboxes[0])

    def test_alias_status_missing(self):
        """Tests for MISSING aliases"""
        # Alias is a mailbox
        status, alias, mailbox = self.view._get_alias_status(
            "foo@example.com", User.objects.none(), AliasCategory.COMMITTEE, [], [], ""
        )
        self.assertEqual(status, AliasStatus.MISSING)
        self.assertIsNone(alias)
        self.assertIsNone(mailbox)

    def test_alias_status_no_comment(self):
        """Tests for NOT_MANAGED_BY_SQUIRE aliases"""
        aliases = [MailcowAlias("foo@example.com", [], 99, public_comment="Foo!")]
        # Alias is not managed by Squire
        status, alias, mailbox = self.view._get_alias_status(
            "foo@example.com", User.objects.none(), AliasCategory.COMMITTEE, aliases, [], "Bar!"
        )
        self.assertEqual(status, AliasStatus.NOT_MANAGED_BY_SQUIRE)
        self.assertIsInstance(alias, MailcowAlias)
        self.assertEqual(alias, aliases[0])
        self.assertIsNone(mailbox)

    def test_alias_status_valid(self):
        """Tests for VALID aliases"""
        aliases = [
            MailcowAlias(
                "foo@example.com", [self.user1.email, self.user2.email, self.user3.email], 99, public_comment="Foo!"
            )
        ]
        # Alias is up-to-date (no archive)
        status, alias, mailbox = self.view._get_alias_status(
            "foo@example.com", User.objects.all(), AliasCategory.COMMITTEE, aliases, [], "Foo!"
        )
        self.assertEqual(status, AliasStatus.VALID)
        self.assertIsInstance(alias, MailcowAlias)
        self.assertEqual(alias, aliases[0])
        self.assertIsNone(mailbox)

        # Alias is up-to-date (preprended archive)
        with override_settings(
            COMMITTEE_CONFIGS={"archive_addresses": ["archief@example.com"], "global_addresses": []}
        ):
            aliases[0].goto = ["archief@example.com"] + aliases[0].goto
            status, alias, mailbox = self.view._get_alias_status(
                "foo@example.com", User.objects.all(), AliasCategory.COMMITTEE, aliases, [], "Foo!"
            )
            self.assertEqual(status, AliasStatus.VALID)
            self.assertIsInstance(alias, MailcowAlias)
            self.assertEqual(alias, aliases[0])
            self.assertIsNone(mailbox)

        # Alias is up-to-date (Ignores committee emails)
        self.view._committee_addresses = [self.user2.email]
        aliases[0].goto = [self.user1.email, self.user3.email]
        status, alias, mailbox = self.view._get_alias_status(
            "foo@example.com", User.objects.all(), AliasCategory.COMMITTEE, aliases, [], "Foo!"
        )
        self.assertEqual(status, AliasStatus.VALID)
        self.assertIsInstance(alias, MailcowAlias)
        self.assertEqual(alias, aliases[0])
        self.assertIsNone(mailbox)

    def test_alias_status_outdated(self):
        """Tests for OUTDATED aliases"""
        aliases = [
            MailcowAlias(
                "foo@example.com", [self.user1.email, self.user3.email, self.user2.email], 99, public_comment="Foo!"
            )
        ]
        # Alias is outdated (different order)
        status, alias, mailbox = self.view._get_alias_status(
            "foo@example.com", User.objects.all(), AliasCategory.COMMITTEE, aliases, [], "Foo!"
        )
        self.assertEqual(status, AliasStatus.OUTDATED)
        self.assertIsInstance(alias, MailcowAlias)
        self.assertEqual(alias, aliases[0])
        self.assertIsNone(mailbox)

        # Alias is outdated (archive missing)
        with override_settings(
            COMMITTEE_CONFIGS={"archive_addresses": ["archief@example.com"], "global_addresses": []}
        ):
            aliases[0].goto = [self.user1.email, self.user2.email, self.user3.email]
            status, alias, mailbox = self.view._get_alias_status(
                "foo@example.com", User.objects.all(), AliasCategory.COMMITTEE, aliases, [], "Foo!"
            )
            self.assertEqual(status, AliasStatus.OUTDATED)
            self.assertIsInstance(alias, MailcowAlias)
            self.assertEqual(alias, aliases[0])
            self.assertIsNone(mailbox)

        # Alias is outdated (Includes committee email)
        self.view._committee_addresses = [self.user2.email]
        aliases[0].goto = [self.user1.email, self.user2.email, self.user3.email]
        status, alias, mailbox = self.view._get_alias_status(
            "foo@example.com", User.objects.all(), AliasCategory.COMMITTEE, aliases, [], "Foo!"
        )
        self.assertEqual(status, AliasStatus.OUTDATED)
        self.assertIsInstance(alias, MailcowAlias)
        self.assertEqual(alias, aliases[0])
        self.assertIsNone(mailbox)


class MailcowSubscriberInfosTests(MailcowStatusViewTests):
    """Tests the MailcowStatusView._get_subscriberinfos_by_status"""

    def test_infos_not_managed(self):
        """Tests subscriberinfos when subscribers are not managed by Squire"""
        alias = MailcowAlias("foo@example.com", goto=["a@example.com", "b@example.com"])
        subinfos = self.view._get_subscriberinfos_by_status(
            AliasStatus.NOT_MANAGED_BY_SQUIRE, User.objects.none(), alias, AliasCategory.MEMBER
        )
        self.assertIn({"name": "a@example.com", "invalid": False}, subinfos)
        self.assertIn({"name": "b@example.com", "invalid": False}, subinfos)
        self.assertEqual(len(subinfos), 2)

    def test_infos_no_subs(self):
        """Tests subscriberinfos when there should be no subscribers"""
        # Mailbox
        subinfos = self.view._get_subscriberinfos_by_status(
            AliasStatus.MAILBOX, User.objects.none(), None, AliasCategory.MEMBER
        )
        self.assertFalse(subinfos)

        # Reserved for another alias
        subinfos = self.view._get_subscriberinfos_by_status(
            AliasStatus.RESERVED, User.objects.none(), None, AliasCategory.MEMBER
        )
        self.assertFalse(subinfos)

    def test_infos_valid(self):
        """Tests subscriberinfos when subscribers are Members"""
        # Member subscribers
        self.view.mailcow_manager.BLOCKLISTED_EMAIL_ADDRESSES = ["foo@example.com"]
        Member.objects.create(first_name="Foo", last_name="Oof", legal_name="Foo Oof", email="foo@example.com")
        Member.objects.create(first_name="Bar", last_name="Rab", legal_name="Bar Rab", email="bar@example.com")
        subinfos = self.view._get_subscriberinfos_by_status(
            AliasStatus.VALID, Member.objects.all(), None, AliasCategory.MEMBER
        )
        self.assertEqual(len(subinfos), 2)
        # Blocklisted email is invalid
        # Data is sorted by name
        self.assertEqual(subinfos[0], {"name": "Bar Rab &mdash; bar@example.com", "invalid": False})
        self.assertEqual(subinfos[1], {"name": "Foo Oof &mdash; foo@example.com", "invalid": True})

        # Committee Subscribers
        AssociationGroup.objects.create(
            name="Boardgamers", type=AssociationGroup.COMMITTEE, contact_email="bg@example.com"
        )
        subinfos = self.view._get_subscriberinfos_by_status(
            AliasStatus.VALID, AssociationGroup.objects.all(), None, AliasCategory.GLOBAL_COMMITTEE
        )
        self.assertEqual(len(subinfos), 1)
        self.assertEqual(subinfos[0], {"name": "Boardgamers (Committee) &mdash; bg@example.com", "invalid": False})


class MailcowStatusExposureTests(MailcowStatusViewTests):
    """Tests exposure route detection"""

    def setUp(self):
        super().setUp()
        self.member_aliases = {
            "foo@example.com": {
                "internal": True,
            },
            "internal@example.com": {"internal": True},
            "public@example.com": {"internal": False},
        }

    def test_exposed_direct(self):
        """Tests if exposure routes are found when there is one direct exposure"""
        aliases = [MailcowAlias("exposer@example.com", ["baz@example.com", "foo@example.com", "abc@example.com"])]

        exposure_routes = self.view._get_alias_exposure_routes("foo@example.com", aliases, [], self.member_aliases)
        self.assertListEqual(exposure_routes, [["exposer@example.com"]])

    def test_exposed_direct_multiple(self):
        """Tests if exposure routes are found when there are multiple direct exposures"""
        aliases = [
            MailcowAlias("exposer1@example.com", ["baz@example.com", "foo@example.com", "abc@example.com"]),
            MailcowAlias("exposer0@example.com", ["foo@example.com", "abc@example.com"]),
            MailcowAlias("exposer2@example.com", ["baz@example.com", "foo@example.com"]),
        ]

        exposure_routes = self.view._get_alias_exposure_routes("foo@example.com", aliases, [], self.member_aliases)
        # Exposed addresses are sorted alphabetically
        self.assertListEqual(
            exposure_routes, [["exposer0@example.com"], ["exposer1@example.com"], ["exposer2@example.com"]]
        )

    def test_member_alias_exposure(self):
        """Tests if exposure routes are found depending on the internal-status of an alias"""
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
        """Tests if exposure routes are found when there is one indirect exposure"""
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
        """Tests if exposure routes are found when there is one indirect exposure"""
        aliases = [
            MailcowAlias("exposed2@example.com", ["baz@example.com", "internal@example.com", "abc@example.com"]),
            MailcowAlias("internal@example.com", ["baz@example.com", "foo@example.com", "abc@example.com"]),
            MailcowAlias("exposed1@example.com", ["baz@example.com", "internal@example.com", "abc@example.com"]),
        ]

        exposure_routes = self.view._get_alias_exposure_routes("foo@example.com", aliases, [], self.member_aliases)
        # Address exposed via [exposed@example.com -> internal@example.com -> foo@example.com]
        self.assertListEqual(
            exposure_routes,
            [["exposed1@example.com", "internal@example.com"], ["exposed2@example.com", "internal@example.com"]],
        )


class MailcowStatusInitializersTests(MailcowStatusViewTests):
    """Tests the MailcowStatusView._init_<foo>_alias_list methods"""

    def setUp(self):
        AssociationGroup.objects.create(
            site_group=Group.objects.create(name="Committee"),
            type=AssociationGroup.COMMITTEE,
            contact_email="bg@example.com",
        )
        super().setUp()

    @patch("mailcow_integration.admin_status.views.MailcowStatusView._get_subscriberinfos_by_status", return_value=[])
    @patch("mailcow_integration.admin_status.views.MailcowStatusView._get_alias_exposure_routes", return_value=[])
    @patch(
        "mailcow_integration.admin_status.views.MailcowStatusView._get_alias_status",
        return_value=(AliasStatus.VALID, None, None),
    )
    @patch(
        "mailcow_integration.squire_mailcow.SquireMailcowManager.get_active_members",
        return_value=Member.objects.none(),
    )
    @patch("mailcow_integration.squire_mailcow.SquireMailcowManager.is_address_internal", return_value=True)
    @override_settings(
        MEMBER_ALIASES={
            "leden@example.com": {
                "title": "Announcements",
                "description": "Cool description",
                "internal": True,
                "allow_opt_out": False,
                "default_opt": True,
                "archive_addresses": ["archive@example.com"],
            },
        }
    )
    def test_init_member_alias_list(
        self, rspamd_mock: Mock, members_mock: Mock, status_mock: Mock, exposure_mock: Mock, subinfos_mock: Mock
    ):
        """Tests initialization for a member alias list"""
        status = self.view._init_member_alias_list(sentinel.aliases, sentinel.mailboxes)

        # Alias status fetched
        status_mock.assert_called_once_with(
            "leden@example.com",
            ANY,
            AliasCategory.MEMBER,
            sentinel.aliases,
            sentinel.mailboxes,
            self.view.mailcow_manager.ALIAS_MEMBERS_PUBLIC_COMMENT,
        )

        # Alias is internal, exposure_routes are calculated
        exposure_mock.assert_called_once_with("leden@example.com", sentinel.aliases, sentinel.mailboxes, ANY)

        # Subinfos calculated once
        subinfos_mock.assert_called_once()

        # AliasInfos returned
        self.assertListEqual(
            status,
            [
                AliasInfos(
                    AliasStatus.VALID.name,
                    [],
                    "leden@example.com",
                    "m_ledenexamplecom",
                    "Announcements",
                    "Cool description",
                    None,
                    True,
                    [],
                    False,
                    archive_addresses=["archive@example.com"],
                )
            ],
        )

        # Address is not internal; extra exposure route should be generated
        with patch("mailcow_integration.squire_mailcow.SquireMailcowManager.is_address_internal", return_value=False):
            status = self.view._init_member_alias_list(sentinel.aliases, sentinel.mailboxes)
            self.assertEqual(len(status), 1)
            self.assertListEqual(
                status[0].exposure_routes, [["leden@example.com", "Alias not located in Rspamd settings map."]]
            )

    @patch("mailcow_integration.admin_status.views.MailcowStatusView._get_subscriberinfos_by_status", return_value=[])
    @patch(
        "mailcow_integration.admin_status.views.MailcowStatusView._get_alias_status",
        return_value=(AliasStatus.VALID, None, None),
    )
    @patch(
        "mailcow_integration.squire_mailcow.SquireMailcowManager.get_active_committees",
        return_value=AssociationGroup.objects.none(),
    )
    @patch("mailcow_integration.squire_mailcow.SquireMailcowManager.is_address_internal", return_value=True)
    @override_settings(
        COMMITTEE_CONFIGS={
            "global_addresses": ["commissies@example.com"],
            "global_archive_addresses": ["archief@example.com"],
        }
    )
    def test_init_global_committee_alias_list(
        self, rspamd_mock: Mock, committees_mock: Mock, status_mock: Mock, subinfos_mock: Mock
    ):
        """Tests initialization for a global committee alias list"""
        status = self.view._init_global_committee_alias_list(sentinel.aliases, sentinel.mailboxes)

        # Alias status fetched
        status_mock.assert_called_once_with(
            "commissies@example.com",
            ANY,
            AliasCategory.GLOBAL_COMMITTEE,
            sentinel.aliases,
            sentinel.mailboxes,
            self.view.mailcow_manager.ALIAS_GLOBAL_COMMITTEE_PUBLIC_COMMENT,
        )

        # Subinfos calculated once
        subinfos_mock.assert_called_once()

        # AliasInfos returned
        self.assertListEqual(
            status,
            [
                AliasInfos(
                    AliasStatus.VALID.name,
                    [],
                    "commissies@example.com",
                    "gc_commissiesexamplecom",
                    "commissies@example.com",
                    "Allows mailing all committees at the same time.",
                    None,
                    internal=True,
                    allow_opt_out=None,
                    archive_addresses=["archief@example.com"],
                )
            ],
        )

        # Address is not internal; extra exposure route should be generated
        with patch("mailcow_integration.squire_mailcow.SquireMailcowManager.is_address_internal", return_value=False):
            status = self.view._init_global_committee_alias_list(sentinel.aliases, sentinel.mailboxes)
            self.assertEqual(len(status), 1)
            self.assertListEqual(
                status[0].exposure_routes, [["commissies@example.com", "Alias not located in Rspamd settings map."]]
            )

    @patch("mailcow_integration.admin_status.views.MailcowStatusView._get_subscriberinfos_by_status", return_value=[])
    @patch(
        "mailcow_integration.admin_status.views.MailcowStatusView._get_alias_status",
        return_value=(AliasStatus.VALID, None, None),
    )
    @patch(
        "mailcow_integration.squire_mailcow.SquireMailcowManager.get_active_committees",
        return_value=AssociationGroup.objects.all(),
    )
    @override_settings(
        COMMITTEE_CONFIGS={
            "archive_addresses": ["archief@example.com"],
        }
    )
    def test_init_committee_alias_list(self, committees_mock: Mock, status_mock: Mock, subinfos_mock: Mock):
        """Tests initialization for a committee alias list"""
        status = self.view._init_committee_alias_list(sentinel.aliases, sentinel.mailboxes)
        committee: AssociationGroup = committees_mock.return_value.first()

        # Alias status fetched
        status_mock.assert_called_once_with(
            committee.contact_email,
            ANY,
            AliasCategory.COMMITTEE,
            sentinel.aliases,
            sentinel.mailboxes,
            self.view.mailcow_manager.ALIAS_COMMITTEE_PUBLIC_COMMENT,
        )

        # Subinfos calculated once
        subinfos_mock.assert_called_once()

        # AliasInfos returned
        self.assertListEqual(
            status,
            [
                AliasInfos(
                    AliasStatus.VALID.name,
                    [],
                    committee.contact_email,
                    "c_" + str(committee.id),
                    committee.name,
                    format_html(
                        "{} ({}): {}", committee.name, committee.get_type_display(), committee.short_description
                    ),
                    None,
                    False,
                    squire_edit_url=reverse("admin:committees_associationgroup_change", args=[committee.id]),
                    archive_addresses=["archief@example.com"],
                )
            ],
        )

    def test_init_orphan_alias_list(self):
        """Tests initialization for a orphaned aliases"""
        # Set up aliases
        aliases = [
            MailcowAlias("notmanaged@example.com", [], public_comment="Foo!"),
            MailcowAlias("leden@example.com", [], public_comment=self.view.mailcow_manager.SQUIRE_MANAGE_INDICATOR),
            MailcowAlias("bg@example.com", [], public_comment=self.view.mailcow_manager.SQUIRE_MANAGE_INDICATOR),
            MailcowAlias(
                "commissies@example.com", [], public_comment=self.view.mailcow_manager.SQUIRE_MANAGE_INDICATOR
            ),
            MailcowAlias(
                "valid@example.com",
                ["goto@example.com"],
                public_comment=self.view.mailcow_manager.SQUIRE_MANAGE_INDICATOR,
                private_comment="hi there!",
            ),
        ]
        member_infos = [AliasInfos(AliasStatus.VALID, [], "leden@example.com", "0", "", "")]
        committee_infos = [AliasInfos(AliasStatus.VALID, [], "bg@example.com", "0", "", "")]
        global_committee_infos = [AliasInfos(AliasStatus.VALID, [], "commissies@example.com", "0", "", "")]

        status = self.view._init_unused_squire_addresses_list(
            aliases, member_infos, committee_infos, global_committee_infos
        )

        # AliasInfos returned.
        #   Skip over aliases not managed by Squire
        #   Skip over aliases used by Squire: Member aliases, committee aliases, global committee aliases
        self.assertListEqual(
            status,
            [
                AliasInfos(
                    AliasStatus.ORPHAN.name,
                    [{"name": "goto@example.com", "invalid": False}],
                    "valid@example.com",
                    "o_validexamplecom",
                    "valid@example.com",
                    "hi there!",
                    aliases[-1],
                    False,
                )
            ],
        )


@patch(
    "mailcow_integration.admin_status.views.MailcowStatusView._init_member_alias_list", return_value=sentinel.m_alias
)
@patch(
    "mailcow_integration.admin_status.views.MailcowStatusView._init_global_committee_alias_list",
    return_value=sentinel.gc_alias,
)
@patch(
    "mailcow_integration.admin_status.views.MailcowStatusView._init_committee_alias_list",
    return_value=sentinel.c_alias,
)
@patch(
    "mailcow_integration.admin_status.views.MailcowStatusView._init_unused_squire_addresses_list",
    return_value=sentinel.o_alias,
)
class MailcowContextDataTests(MailcowStatusViewTests):
    """Tests context data generation"""

    @patch("mailcow_integration.squire_mailcow.SquireMailcowManager.get_alias_all", return_value=[1])
    @patch("mailcow_integration.squire_mailcow.SquireMailcowManager.get_mailbox_all", return_value=[2])
    @patch(
        "mailcow_integration.squire_mailcow.SquireMailcowManager.get_internal_alias_rspamd_settings",
        return_value=(None, None),
    )
    def test_get_context_data_valid(
        self,
        mock_rspamd: Mock,
        mock_mailboxes: Mock,
        mock_aliases: Mock,
        mock_orphan: Mock,
        mock_comm: Mock,
        mock_global_comm: Mock,
        mock_member: Mock,
    ):
        """Tests the view's get_context_data"""
        self.view.get_context_data()

        # Mailbox/alias data retrieved once, ignoring the cache
        mock_aliases.assert_called_once_with(use_cache=False)
        mock_mailboxes.assert_called_once_with(use_cache=False)

        # No API errors: Init list methods called once
        mock_member.assert_called_once_with([1], [2])
        mock_global_comm.assert_called_once_with([1], [2])
        mock_comm.assert_called_once_with([1], [2])
        mock_orphan.assert_called_once_with([1], sentinel.m_alias, sentinel.c_alias, sentinel.gc_alias)

    def _test_exception_not_call_list_init(
        self,
        exception: MailcowException,
        error_message: str,
        mock_orphan: Mock,
        mock_comm: Mock,
        mock_global_comm: Mock,
        mock_member: Mock,
    ):
        """Tests whether a given exception is handled with the given message"""
        with patch("mailcow_integration.squire_mailcow.SquireMailcowManager.get_alias_all", side_effect=exception):
            context = self.view.get_context_data()
            # Error message present in the context
            self.assertIn("error", context)
            self.assertEqual(context["error"], error_message)

            # Init list methods not called
            mock_member.assert_not_called()
            mock_global_comm.assert_not_called()
            mock_comm.assert_not_called()
            mock_orphan.assert_not_called()

    @suppress_errors(logger_name="mailcow_integration.admin_status.views")
    def test_get_context_data_exceptions(
        self, mock_orphan: Mock, mock_comm: Mock, mock_global_comm: Mock, mock_member: Mock
    ):
        """Tests exception handling in get_context_data"""
        # Auth exception
        self._test_exception_not_call_list_init(
            MailcowAuthException(), "No valid API key set.", mock_orphan, mock_comm, mock_global_comm, mock_member
        )

        # R/W Access denied
        self._test_exception_not_call_list_init(
            MailcowAPIReadWriteAccessDenied(),
            "API key only allows access to read operations, not write.",
            mock_orphan,
            mock_comm,
            mock_global_comm,
            mock_member,
        )

        # API Access denied for IP
        self._test_exception_not_call_list_init(
            MailcowAPIAccessDenied("invalid ip oh noes: 1234"),
            "IP address is not whitelisted in the Mailcow admin: 1234",
            mock_orphan,
            mock_comm,
            mock_global_comm,
            mock_member,
        )

        # Unknown exception
        self._test_exception_not_call_list_init(
            MailcowException("something went wrong!"),
            "something went wrong!",
            mock_orphan,
            mock_comm,
            mock_global_comm,
            mock_member,
        )


@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_member_aliases", return_value=[])
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_global_committee_aliases", return_value=[])
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_committee_aliases", return_value=[])
@patch("mailcow_integration.squire_mailcow.SquireMailcowManager.delete_aliases", return_value=None)
@patch(
    "mailcow_integration.admin_status.views.MailcowStatusView.get_context_data",
    return_value={"unused_aliases": [MailcowAlias("unused@example.com", [])]},
)
@patch("django.contrib.messages.success")  # Messages middelware doesn't activate when using RequestFactory
@patch("django.contrib.messages.error")
class MailcowStatusPostTests(MailcowStatusViewTests):
    """Tests POST requests on the status page"""

    def test_post_update_aliases_member(
        self, _, __, mock_context: Mock, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock
    ):
        """Tests if member aliases are updated when requested"""
        self.request = RequestFactory().post("/status", data={"alias_type": "members"})
        res = self.view.dispatch(self.request)

        # Correct methods called
        mock_m.assert_called_once()
        mock_gc.assert_not_called()
        mock_c.assert_not_called()
        mock_o.assert_not_called()
        mock_context.assert_not_called()

        # Redirect
        self.assertEqual(res.status_code, 302)

    def test_post_update_aliases_global_committee(
        self, _, __, mock_context: Mock, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock
    ):
        """Tests if global committee aliases are updated when requested"""
        self.request = RequestFactory().post("/status", data={"alias_type": "global_committee"})
        res = self.view.dispatch(self.request)

        # Correct methods called
        mock_m.assert_not_called()
        mock_gc.assert_called_once()
        mock_c.assert_not_called()
        mock_o.assert_not_called()
        mock_context.assert_not_called()

        # Redirect
        self.assertEqual(res.status_code, 302)

    def test_post_update_aliases_committee(
        self, _, __, mock_context: Mock, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock
    ):
        """Tests if committee aliases are updated when requested"""
        self.request = RequestFactory().post("/status", data={"alias_type": "committees"})
        res = self.view.dispatch(self.request)

        # Correct methods called
        mock_m.assert_not_called()
        mock_gc.assert_not_called()
        mock_c.assert_called_once()
        mock_o.assert_not_called()
        mock_context.assert_not_called()

        # Redirect
        self.assertEqual(res.status_code, 302)

    def test_post_delete_aliases_orphan(
        self, _, __, mock_context: Mock, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock
    ):
        """Tests if orphan aliases are deleted when requested"""
        self.request = RequestFactory().post("/status", data={"alias_type": "orphan"})
        res = self.view.dispatch(self.request)

        # Correct methods called
        mock_m.assert_not_called()
        mock_gc.assert_not_called()
        mock_c.assert_not_called()
        mock_o.assert_called_once_with(["unused@example.com"], self.view.mailcow_manager.SQUIRE_MANAGE_INDICATOR)
        mock_context.assert_called_once()

        # Redirect
        self.assertEqual(res.status_code, 302)

    @patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_internal_addresses", return_value=None)
    def test_post_update_rspamd(
        self, mock_rspamd: Mock, _, __, mock_context: Mock, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock
    ):
        """Tests if the internal Rspamd rule is updated when requested"""
        self.request = RequestFactory().post("/status", data={"alias_type": "internal_alias"})
        res = self.view.dispatch(self.request)

        # Correct methods called
        mock_m.assert_not_called()
        mock_gc.assert_not_called()
        mock_c.assert_not_called()
        mock_o.assert_not_called()
        mock_context.assert_not_called()
        mock_rspamd.assert_called_once()

        # Redirect
        self.assertEqual(res.status_code, 302)

    def test_post_invalid(self, _, __, mock_context: Mock, mock_o: Mock, mock_c: Mock, mock_gc: Mock, mock_m: Mock):
        """Tests if no methods are called if invalid data is passed"""
        self.request = RequestFactory().post("/status", data={})
        res = self.view.dispatch(self.request)

        # Correct methods called
        mock_m.assert_not_called()
        mock_gc.assert_not_called()
        mock_c.assert_not_called()
        mock_o.assert_not_called()
        mock_context.assert_not_called()

        # HTTP Bad Request
        self.assertEqual(res.status_code, 400)
