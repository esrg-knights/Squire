from django.contrib.auth import get_user_model
from django.test import TestCase
from dynamic_preferences.users.models import UserPreferenceModel

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
