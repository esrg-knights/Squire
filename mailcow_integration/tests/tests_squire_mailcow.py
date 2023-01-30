from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from dynamic_preferences.users.models import UserPreferenceModel
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

    @patch('mailcow_integration.api.client.MailcowAPIClient.get_rspamd_setting_all', return_value=iter([
        RspamdSettings(999, "Other rule", "RULE 1", True),
        RspamdSettings(234, "[MANAGED BY SQUIRE] Other thing", "RULE 2", True),
        RspamdSettings(567, "[MANAGED BY SQUIRE] Internal Alias", "RULE 3", True),
        RspamdSettings(890, "Another rule", "RULE 4", True),
    ]))
    def test_get_rspamd_setting(self, mock_get: Mock):
        """ Tests whether the correct Rspamd setting can be found by Squire """
        setting = self.squire_mailcow_manager._get_rspamd_internal_alias_setting()
        self.assertIsNotNone(setting)
        self.assertEqual(setting.id, 567)

        mock_get.assert_called_once()

        # Setting should not be found if no descriptions match
        with patch('mailcow_integration.squire_mailcow.SquireMailcowManager.INTERNAL_ALIAS_SETTING_NAME', '[MANAGED BY SQUIRE] fake name'):
            self.assertIsNone(self.squire_mailcow_manager._get_rspamd_internal_alias_setting())

    @patch('mailcow_integration.api.client.MailcowAPIClient.create_rspamd_setting')
    @patch('mailcow_integration.api.client.MailcowAPIClient.update_rspamd_setting')
    def test_set_internal_adresses(self, mock_update: Mock, mock_create: Mock):
        """ Tests whether the internal aliases are correctly updated """
        self.squire_mailcow_manager._internal_aliases = ['foo@example.com', 'bar@example.com']
        rule = "foobar\nrcpt = \"/^(foo@example\\.com|bar@example\\.com)$/\"fooadsfasdf"
        setting = RspamdSettings(999, "Other rule", rule, True)

        # Setting is active and rule addresses are up-to-date
        with patch('mailcow_integration.squire_mailcow.SquireMailcowManager._get_rspamd_internal_alias_setting',
                return_value=setting) as get_alias_setting:
            self.assertIsNone(self.squire_mailcow_manager.set_internal_addresses())
            get_alias_setting.assert_called_once()
            # Create/update methods should not be called
            mock_create.assert_not_called()
            mock_update.assert_not_called()

        # Setting is inactive
        setting.active = False
        with patch('mailcow_integration.squire_mailcow.SquireMailcowManager._get_rspamd_internal_alias_setting',
                return_value=setting) as get_alias_setting:
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
        with patch('mailcow_integration.squire_mailcow.SquireMailcowManager._get_rspamd_internal_alias_setting',
                return_value=setting) as get_alias_setting:
            self.squire_mailcow_manager.set_internal_addresses()
            # Create/update methods should not be called
            mock_create.assert_not_called()
            mock_update.assert_called_once()
            # Updated rule should have correct addresses set
            self.assertIn("\"/^(foo@example\\.com|bar@example\\.com)$/\"", mock_update.call_args.args[0].content)

        # Setting does not exist
        mock_update.reset_mock()
        with patch('mailcow_integration.squire_mailcow.SquireMailcowManager._get_rspamd_internal_alias_setting',
                return_value=None) as get_alias_setting:
            self.squire_mailcow_manager.set_internal_addresses()
            # Create/update methods should not be called
            mock_create.assert_called_once()
            mock_update.assert_not_called()
