from copy import deepcopy
from typing import List
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from dynamic_preferences.users.models import UserPreferenceModel
from unittest.mock import Mock, PropertyMock, patch, ANY
from committees.models import AssociationGroup, AssociationGroupMembership
from core.tests.util import suppress_infos, suppress_warnings

from mailcow_integration.api.interface.alias import MailcowAlias
from mailcow_integration.api.interface.mailbox import MailcowMailbox
from mailcow_integration.api.interface.rspamd import RspamdSettings
from mailcow_integration.squire_mailcow import SquireMailcowManager
from membership_file.models import Member

User = get_user_model()

##################################################################################
# Test cases for Squire's MailcowManager
# @since 23 JAN 2023
##################################################################################


class SquireMailcowManagerTest(TestCase):
    """ Tests the Squire Mailcow Manager """

    def setUp(self):
        self.squire_mailcow_manager = SquireMailcowManager(mailcow_host="example.com", mailcow_api_key="fake_key")

    def _setup_subs(self, default_opt: bool):
        """ Setup subscription preferences test data.
            Creates one member with a preference for: opt-in, opt-out, no preference set, not linked to a user
        """
        foo = User.objects.create(username="foo")
        bar = User.objects.create(username="bar")
        baz = User.objects.create(username="baz")

        Member.objects.create(user=foo, first_name='Subbed', last_name="Foo", legal_name="Subbed Foo", email="foo@example.com")
        Member.objects.create(user=bar, first_name='Unsubbed', last_name="Bar", legal_name="Unsubbed Bar", email="bar@example.com")
        Member.objects.create(user=baz, first_name='NoPref', last_name="Baz", legal_name="NoPref Baz", email="baz@example.com")
        Member.objects.create(user=None, first_name='NoUser', last_name="Moo", legal_name="NoUser Moo", email="moo@example.com")

        UserPreferenceModel.objects.create(instance=foo, name="mycategoryexamplecom", raw_value="True", section="mail")
        UserPreferenceModel.objects.create(instance=bar, name="mycategoryexamplecom", raw_value="False", section="mail")

        return self.squire_mailcow_manager.get_subscribed_members(Member.objects.all(), "mycategoryexamplecom", default_opt)

    ################
    # HELPER METHODS
    ################
    def test_subscribed_members_default_opt_in(self):
        """ Tests whether the correct members are returned based on their
            subscription preferences when the default is opt-in
        """
        subs = self._setup_subs(True)

        # Default is opt-in, so those without a preference must also be present
        expected_subs = Member.objects.filter(first_name__in=['Subbed', 'NoPref', 'NoUser'])
        self.assertQuerysetEqual(subs, expected_subs)

    def test_subscribed_members_default_opt_out(self):
        """ Tests whether the correct members are returned based on their
            subscription preferences when the default is opt-out
        """
        subs = self._setup_subs(False)

        # Default is opt-out, so those only those with an opt-in preference should be present
        expected_subs = Member.objects.filter(first_name__in=['Subbed'])
        self.assertQuerysetEqual(subs, expected_subs)

    def test_str(self):
        """ Tests the __str__ method """
        self.assertEqual(str(self.squire_mailcow_manager), "SquireMailcowManager[example.com]")

    def test_host_prop(self):
        """ Tests the mailcow_host prop """
        self.assertEqual(self.squire_mailcow_manager.mailcow_host, "example.com")

    def test_email_clean(self):
        """ Tests the various clean_<foo> methods """
        # Setup blocklist and model instances
        self.squire_mailcow_manager.BLOCKLISTED_EMAIL_ADDRESSES = ["foo@example.com", "bar@example.com"]
        User.objects.create(username="foo", email="foo@example.com")
        User.objects.create(username="bar", email="bar@example.com")
        baz = User.objects.create(username="baz", email="baz@example.com")
        baq = User.objects.create(username="baq", email="baq@example.com")

        cleaned = self.squire_mailcow_manager.clean_emails(User.objects.all(), email_field="email")
        # Blocklisted email addresses are filtered out
        self.assertQuerysetEqual(cleaned, User.objects.filter(email__in=[baz.email, baq.email]), ordered=False)

        # Items in the queryset are sorted by email
        self.assertEqual(cleaned[0].email, "baq@example.com")

        # Flat variant only contains email addresses (and is also sorted)
        cleaned_flat = self.squire_mailcow_manager.clean_emails_flat(User.objects.all(), email_field="email")
        self.assertListEqual(cleaned_flat, ["baq@example.com", "baz@example.com"])

    @patch("membership_file.models.Member.objects.filter_active")
    def test_get_active_members(self, mock: Mock):
        """ Tests if get_active_members directly invokes get_active of the MemberManager """
        self.squire_mailcow_manager.get_active_members()
        mock.assert_called_once()

    def test_get_active_committees(self):
        """ Tests whether only a specific group of committtees are considered for email aliases """
        committee = AssociationGroup.objects.create(site_group=Group.objects.create(name="Dummy Group0"),
            type=AssociationGroup.COMMITTEE, contact_email="c@example.com")
        order = AssociationGroup.objects.create(site_group=Group.objects.create(name="Dummy Group1"),
            type=AssociationGroup.GUILD, contact_email="o@example.com")
        workgroup = AssociationGroup.objects.create(site_group=Group.objects.create(name="Dummy Group2"),
            type=AssociationGroup.WORKGROUP, contact_email="w@example.com")
        board = AssociationGroup.objects.create(site_group=Group.objects.create(name="Dummy Group3"),
            type=AssociationGroup.BOARD, contact_email="b@example.com")
        no_address = AssociationGroup.objects.create(site_group=Group.objects.create(name="Dummy Group4"),
            type=AssociationGroup.COMMITTEE)

        valid_assoc_groups = self.squire_mailcow_manager.get_active_committees()
        self.assertIn(committee, valid_assoc_groups)
        self.assertIn(order, valid_assoc_groups)
        self.assertIn(workgroup, valid_assoc_groups)
        self.assertNotIn(board, valid_assoc_groups)
        self.assertNotIn(no_address, valid_assoc_groups)

    ################
    # RSPAMD
    ################
    @patch('mailcow_integration.api.client.MailcowAPIClient.get_rspamd_setting_all', return_value=iter([
        # NOTE: Wrap list in iterable to match function signature (it returns a generator, not a list)
        RspamdSettings(999, "Other rule", "RULE 1", True),
        RspamdSettings(234, "[MANAGED BY SQUIRE] Other thing", "RULE 2", True),
        RspamdSettings(567, "[MANAGED BY SQUIRE] Internal Alias", "RULE 3", True),
        RspamdSettings(890, "Another rule", "RULE 4", True),
    ]))
    def test_get_rspamd_setting(self, mock_get: Mock):
        """ Tests whether the correct Rspamd setting can be found by Squire """
        setting = self.squire_mailcow_manager._internal_alias_rspamd_setting
        self.assertIsNotNone(setting)
        self.assertEqual(setting.id, 567)

        mock_get.assert_called_once()

        # Setting should not be found if no descriptions match
        with patch('mailcow_integration.squire_mailcow.SquireMailcowManager.INTERNAL_ALIAS_SETTING_NAME', '[MANAGED BY SQUIRE] fake name'):
            self.assertIsNone(self.squire_mailcow_manager._internal_alias_rspamd_setting)

    @patch('mailcow_integration.api.client.MailcowAPIClient.create_rspamd_setting')
    @patch('mailcow_integration.api.client.MailcowAPIClient.update_rspamd_setting')
    def test_set_internal_adresses(self, mock_update: Mock, mock_create: Mock):
        """ Tests whether the internal aliases are correctly updated """
        self.squire_mailcow_manager.INTERNAL_ALIAS_ADDRESSES = ['foo@example.com', 'bar@example.com']
        rule = "foobar\nrcpt = \"/^(foo@example\\.com|bar@example\\.com)$/\"fooadsfasdf"
        setting = RspamdSettings(999, "Other rule", rule, True)

        # Setting is active and rule addresses are up-to-date
        with patch('mailcow_integration.squire_mailcow.SquireMailcowManager._internal_alias_rspamd_setting',
                return_value=setting, new_callable=PropertyMock) as setting_prop:
            # Verify return value, and that the property is only called once.
            self.assertIsNone(self.squire_mailcow_manager.set_internal_addresses())
            setting_prop.assert_called_once()
            # Create/update methods should not be called
            mock_create.assert_not_called()
            mock_update.assert_not_called()

        # Setting is inactive
        setting.active = False
        with patch('mailcow_integration.squire_mailcow.SquireMailcowManager._internal_alias_rspamd_setting',
                return_value=setting, new_callable=PropertyMock):
            self.squire_mailcow_manager.set_internal_addresses()
            # Create/update methods should not be called
            mock_create.assert_not_called()
            mock_update.assert_called_once()
            # Updated rule should be active
            self.assertTrue(mock_update.call_args.args[0].active)

        # Setting addresses out-of-date
        mock_update.reset_mock()
        setting.active = True
        setting.content = "out of date"
        with patch('mailcow_integration.squire_mailcow.SquireMailcowManager._internal_alias_rspamd_setting',
                return_value=setting, new_callable=PropertyMock):
            self.squire_mailcow_manager.set_internal_addresses()
            # Create/update methods should not be called
            mock_create.assert_not_called()
            mock_update.assert_called_once()
            # Updated rule should have correct addresses set
            self.assertIn("\"/^(foo@example\\.com|bar@example\\.com)$/\"", mock_update.call_args.args[0].content)

        # Setting does not exist
        mock_update.reset_mock()
        with patch('mailcow_integration.squire_mailcow.SquireMailcowManager._internal_alias_rspamd_setting',
                return_value=None, new_callable=PropertyMock):
            self.squire_mailcow_manager.set_internal_addresses()
            # Create/update methods should not be called
            mock_create.assert_called_once()
            mock_update.assert_not_called()

    ################
    # ALIASES/MAILBOX CACHING
    ################
    @patch('mailcow_integration.api.client.MailcowAPIClient.get_alias_all', return_value=iter([
        MailcowAlias("foo@example.com", ["a@example.com", "b@example.com"], 99),
        MailcowAlias("bar@example.com", ["x@example.com", "y@example.com"], 100),
    ]))
    def test_get_alias_all(self, mock_get: Mock):
        """ Tests the caching behaviour of get_alias_all """
        # Cache is empty, so should make a request. Caches should be set accordingly
        self.squire_mailcow_manager._alias_cache = None
        self.squire_mailcow_manager._alias_map_cache = {"foo": "bar"}
        self.squire_mailcow_manager.get_alias_all(use_cache=True)
        mock_get.assert_called_once()
        self.assertIsNotNone(self.squire_mailcow_manager._alias_cache)
        self.assertIsNotNone(any(1 for alias in self.squire_mailcow_manager._alias_cache if alias.id == 99), None)
        self.assertIsNotNone(any(1 for alias in self.squire_mailcow_manager._alias_cache if alias.id == 100), None)
        self.assertIsNone(self.squire_mailcow_manager._alias_map_cache)
        alias_cache = deepcopy(self.squire_mailcow_manager._alias_cache)

        # Cache is not empty, so should not make a request
        mock_get.reset_mock()
        aliases = self.squire_mailcow_manager.get_alias_all(use_cache=True)
        mock_get.assert_not_called()
        self.assertListEqual(aliases, alias_cache) # Cache wasn't modified

        # Cache is not empty, but use_cache=False
        mock_get.reset_mock()
        alias_cache = self.squire_mailcow_manager._alias_cache
        aliases = self.squire_mailcow_manager.get_alias_all(use_cache=False)
        mock_get.assert_called_once()
        # Cache should be regenerated (compare list identities)
        self.assertNotEqual(aliases, alias_cache)

    @patch('mailcow_integration.api.client.MailcowAPIClient.get_mailbox_all', return_value=iter([
        MailcowMailbox("foo@example.com", "Mr. Foo"),
        MailcowMailbox("bar@example.com", "Sir Bar"),
    ]))
    def test_get_mailbox_all(self, mock_get: Mock):
        """ Tests the caching behaviour of get_mailbox_all """
        # Cache is empty, so should make a request. Caches should be set accordingly
        self.squire_mailcow_manager._mailbox_cache = None
        self.squire_mailcow_manager._mailbox_map_cache = {"foo": "bar"}
        self.squire_mailcow_manager.get_mailbox_all(use_cache=True)
        mock_get.assert_called_once()
        self.assertIsNotNone(self.squire_mailcow_manager._mailbox_cache)
        self.assertIsNotNone(any(1 for mailbox in self.squire_mailcow_manager._mailbox_cache if mailbox.username == "foo@example.com"), None)
        self.assertIsNotNone(any(1 for mailbox in self.squire_mailcow_manager._mailbox_cache if mailbox.username == "bar@example.com"), None)
        self.assertIsNone(self.squire_mailcow_manager._mailbox_map_cache)
        mailbox_cache = deepcopy(self.squire_mailcow_manager._mailbox_cache)

        # Cache is not empty, so should not make a request
        mock_get.reset_mock()
        mailboxes = self.squire_mailcow_manager.get_mailbox_all(use_cache=True)
        mock_get.assert_not_called()
        self.assertListEqual(mailboxes, mailbox_cache) # Cache wasn't modified

        # Cache is not empty, but use_cache=False
        mock_get.reset_mock()
        mailbox_cache = self.squire_mailcow_manager._mailbox_cache
        mailboxes = self.squire_mailcow_manager.get_mailbox_all(use_cache=False)
        mock_get.assert_called_once()
        # Cache should be regenerated (compare list identities)
        self.assertNotEqual(mailboxes, mailbox_cache)

    @patch('mailcow_integration.squire_mailcow.SquireMailcowManager.get_alias_all', return_value=iter([
        MailcowAlias("foo@example.com", ["a@example.com", "b@example.com"], 99),
        MailcowAlias("bar@example.com", ["x@example.com", "y@example.com"], 100),
    ]))
    def test_alias_map_prop(self, mock_get: Mock):
        """ Tests the caching behaviour of alias_map """
        # Cache is empty, so should make a request. Caches should be set accordingly
        self.squire_mailcow_manager.alias_map
        mock_get.assert_called_once()
        self.assertIsNotNone(self.squire_mailcow_manager._alias_map_cache)
        self.assertEqual(len(self.squire_mailcow_manager._alias_map_cache), 2)
        self.assertIsNotNone(self.squire_mailcow_manager._alias_map_cache["foo@example.com"])
        self.assertIsNotNone(self.squire_mailcow_manager._alias_map_cache["bar@example.com"])
        alias_cache = deepcopy(self.squire_mailcow_manager._alias_map_cache)

        # Cache is not empty, so should not make a request
        mock_get.reset_mock()
        self.squire_mailcow_manager._alias_cache = "dummy"
        aliases = self.squire_mailcow_manager.alias_map
        mock_get.assert_not_called()
        self.assertDictEqual(aliases, alias_cache) # Cache wasn't modified

        # Alias cache was invalidated
        mock_get.reset_mock()
        self.squire_mailcow_manager._alias_cache = None
        self.squire_mailcow_manager.alias_map
        mock_get.assert_called_once()
        self.assertIsNotNone(self.squire_mailcow_manager._alias_map_cache)

    @patch('mailcow_integration.squire_mailcow.SquireMailcowManager.get_mailbox_all', return_value=iter([
        MailcowMailbox("foo@example.com", "Mr. Foo"),
        MailcowMailbox("bar@example.com", "Sir Bar"),
    ]))
    def test_mailbox_map_prop(self, mock_get: Mock):
        """ Tests the caching behaviour of mailbox_map """
        # Cache is empty, so should make a request. Caches should be set accordingly
        self.squire_mailcow_manager.mailbox_map
        mock_get.assert_called_once()
        self.assertIsNotNone(self.squire_mailcow_manager._mailbox_map_cache)
        self.assertEqual(len(self.squire_mailcow_manager._mailbox_map_cache), 2)
        self.assertIsNotNone(self.squire_mailcow_manager._mailbox_map_cache["foo@example.com"])
        self.assertIsNotNone(self.squire_mailcow_manager._mailbox_map_cache["bar@example.com"])
        mailbox_cache = deepcopy(self.squire_mailcow_manager._mailbox_map_cache)

        # Cache is not empty, so should not make a request
        mock_get.reset_mock()
        self.squire_mailcow_manager._mailbox_cache = "dummy"
        mailboxes = self.squire_mailcow_manager.mailbox_map
        mock_get.assert_not_called()
        self.assertDictEqual(mailboxes, mailbox_cache) # Cache wasn't modified

        # Mailbox cache was invalidated
        mock_get.reset_mock()
        self.squire_mailcow_manager._mailbox_cache = None
        self.squire_mailcow_manager.mailbox_map
        mock_get.assert_called_once()
        self.assertIsNotNone(self.squire_mailcow_manager._mailbox_map_cache)

    ################
    # Updating aliases
    ################
    @patch('mailcow_integration.api.client.MailcowAPIClient.create_alias')
    @patch('mailcow_integration.api.client.MailcowAPIClient.update_alias')
    @patch('mailcow_integration.squire_mailcow.SquireMailcowManager.alias_map', return_value={
        "foo@example.com": MailcowAlias("foo@example.com", ["a@example.com", "b@example.com"], 99, public_comment="Foo!"),
    }, new_callable=PropertyMock)
    @patch('mailcow_integration.squire_mailcow.SquireMailcowManager.mailbox_map', return_value={}, new_callable=PropertyMock)
    @suppress_warnings(logger_name="mailcow_integration.squire_mailcow")
    def test_set_alias_by_name(self, mock_mailbox_map: Mock, mock_alias_map: Mock,
            mock_update: Mock, mock_create: Mock):
        """ Tests the way aliases are updated/created """
        # New alias created
        self.squire_mailcow_manager._set_alias_by_name("new@example.com", ["a@example.com", "b@example.com"], "Foo!")
        mock_create.assert_called_once()
        mock_update.assert_not_called()
        self.assertTrue(mock_create.call_args.args)
        alias: MailcowAlias = mock_create.call_args.args[0]
        self.assertIsInstance(alias, MailcowAlias)
        self.assertEqual(alias.address, "new@example.com")
        self.assertEqual(alias.goto, ["a@example.com", "b@example.com"])
        self.assertEqual(alias.public_comment, "Foo!")
        self.assertTrue(alias.active)
        self.assertFalse(alias.sogo_visible)
        mock_create.reset_mock()

        # Public comment does not match up
        self.squire_mailcow_manager._set_alias_by_name("foo@example.com", ["c@example.com", "d@example.com"], "Bar!")
        mock_create.assert_not_called()
        mock_update.assert_not_called()

        # Alias updated successfully
        self.squire_mailcow_manager._set_alias_by_name("foo@example.com", ["c@example.com", "d@example.com"], "Foo!")
        mock_create.assert_not_called()
        alias = mock_alias_map.return_value["foo@example.com"] # Should re-use existing alias
        mock_update.assert_called_once_with(alias)
        self.assertEqual(alias.address, "foo@example.com")
        self.assertEqual(alias.goto, ["c@example.com", "d@example.com"])
        self.assertEqual(alias.public_comment, "Foo!")
        self.assertTrue(alias.active)
        self.assertFalse(alias.sogo_visible)
        mock_update.reset_mock()

        # goto is empty (failsafe)
        self.squire_mailcow_manager._set_alias_by_name("foo@example.com", [], "Foo!")
        mock_create.assert_not_called()
        alias = mock_alias_map.return_value["foo@example.com"] # Should re-use existing alias
        mock_update.assert_called_once_with(alias)
        self.assertEqual(alias.address, "foo@example.com")
        self.assertEqual(alias.goto, ["c@example.com", "d@example.com"]) # Previous goto addresses remain
        self.assertEqual(alias.public_comment, "Foo!")
        self.assertFalse(alias.active) # Alias made inactive
        self.assertFalse(alias.sogo_visible)
        mock_update.reset_mock()

    @patch('mailcow_integration.squire_mailcow.SquireMailcowManager.get_archive_adresses_for_type', return_value=[
        'archive@example.com', 'archive2@example.com'
    ])
    @patch('mailcow_integration.squire_mailcow.SquireMailcowManager.mailbox_map', return_value={
        "foo@example.com": MailcowMailbox("mailbox@example.com", "Mr. Foo"),
    }, new_callable=PropertyMock)
    @patch('mailcow_integration.squire_mailcow.SquireMailcowManager._set_alias_by_name')
    @suppress_infos(logger_name="mailcow_integration.squire_mailcow")
    def test_update_committee_aliases(self, mock_set_alias: Mock, mock_mailbox_map: Mock, archive_mock: Mock):
        """ Tests updating committee aliases """
        self.squire_mailcow_manager.BLOCKLISTED_EMAIL_ADDRESSES = ["blocklisted@example.com"]
        # Setup committees:
        #   - boardgames: foo, bar
        #   - roleplay: foo
        #   - blocked: bar
        bg = AssociationGroup.objects.create(site_group=Group.objects.create(name="Boardgamers"),
            type=AssociationGroup.COMMITTEE, contact_email="bg@example.com")
        rp = AssociationGroup.objects.create(site_group=Group.objects.create(name="Roleplayers"),
            type=AssociationGroup.COMMITTEE, contact_email="rp@example.com")
        mailbox = AssociationGroup.objects.create(site_group=Group.objects.create(name="Mailbox"),
            type=AssociationGroup.COMMITTEE, contact_email="mailbox@example.com")
        blocked = AssociationGroup.objects.create(site_group=Group.objects.create(name="Blocklisted"),
            type=AssociationGroup.COMMITTEE, contact_email="blocklisted@example.com")
        foo = Member.objects.create(first_name='Foo', last_name="Oof", legal_name="Foo Oof", email="memberfoo@example.com")
        bar = Member.objects.create(first_name='Bar', last_name="Rab", legal_name="Bar Rab", email="memberbar@example.com")
        blockedmem = Member.objects.create(first_name='Blocked', last_name="Dekcolb", legal_name="Blocked Dekcolb", email="blocklisted@example.com")
        AssociationGroupMembership.objects.create(member=foo, group=bg)
        AssociationGroupMembership.objects.create(member=bar, group=bg)
        AssociationGroupMembership.objects.create(member=foo, group=rp)
        AssociationGroupMembership.objects.create(member=blockedmem, group=rp)
        AssociationGroupMembership.objects.create(member=bar, group=blocked)

        self.squire_mailcow_manager.update_committee_aliases()
        # Blockedlisted member email not used
        mock_set_alias.assert_any_call("bg@example.com", archive_mock.return_value + ["memberbar@example.com", "memberfoo@example.com"],
            public_comment=self.squire_mailcow_manager.ALIAS_COMMITTEE_PUBLIC_COMMENT)
        mock_set_alias.assert_any_call("rp@example.com", archive_mock.return_value + ["memberfoo@example.com"],
            public_comment=self.squire_mailcow_manager.ALIAS_COMMITTEE_PUBLIC_COMMENT)
        # Blocklisted committee email not called
        self.assertEqual(mock_set_alias.call_count, 2)

        # Alias cache is invalidated
        self.assertIsNone(self.squire_mailcow_manager._alias_cache)
