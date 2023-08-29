from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from unittest.mock import patch, Mock
from mailcow_integration.account_pages.forms import MemberMailPreferencesForm

from mailcow_integration.account_pages.views import EmailPreferencesChangeView
from mailcow_integration.dynamic_preferences_registry import register_preferences
from mailcow_integration.squire_mailcow import SquireMailcowManager

User = get_user_model()


@override_settings(
    MEMBER_ALIASES={
        "leden@example.com": {
            "title": "Announcements",
            "description": "Cool description",
            "internal": True,
            "allow_opt_out": True,
            "default_opt": True,
            "archive_addresses": ["archive@example.com"],
        },
    }
)
class MemberMailPreferencesTests(TestCase):
    """Tests members updating their mail preferences"""

    def setUp(self):
        user = User.objects.create(username="user")
        self.request = RequestFactory().get("/updatepref")
        self.request.user = user
        self.view = EmailPreferencesChangeView(success_url="foo")
        self.view.setup(self.request)
        self.view.mailcow_manager = SquireMailcowManager(mailcow_host="example.com", mailcow_api_key="fake_key")

        register_preferences(settings.MEMBER_ALIASES)

    @patch("mailcow_integration.account_pages.forms.MemberMailPreferencesForm.update_preferences")
    @patch("django.contrib.messages.success")  # Messages middleware doesn't activate when using RequestFactory
    def test_update_preferences_called(self, _, update_pref: Mock):
        """Tests if update_preferences is called when the form in the view is valid"""
        form = self.view.get_form()
        self.assertIsInstance(form, MemberMailPreferencesForm)
        self.view.form_valid(form)
        update_pref.assert_called_once()

    @patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_member_aliases")
    def test_mailcowmanager_invoked_nochange(self, update_alias: Mock):
        """Tests if the Mailcow Manager is not invoked when there aren't any changes"""
        form_class = self.view.get_form_class()
        form_data = {"mail__ledenexamplecom": False}
        form = form_class(initial=form_data, data=form_data, mailcow_manager=self.view.mailcow_manager)

        self.assertTrue(form.is_valid())
        form.update_preferences()
        # Form hasn't changed, so MailcowManager shouldn't be invoked
        update_alias.assert_not_called()

    @patch("mailcow_integration.squire_mailcow.SquireMailcowManager.update_member_aliases")
    def test_mailcowmanager_invoked_change(self, update_alias: Mock):
        """Tests if the Mailcow Manager is not invoked when there are changes"""
        form_class = self.view.get_form_class()
        form_data = {"mail__ledenexamplecom": False}
        initial_data = {"mail__ledenexamplecom": True}
        form = form_class(initial=initial_data, data=form_data, mailcow_manager=self.view.mailcow_manager)

        self.assertTrue(form.is_valid())
        form.update_preferences()
        # Form changed, so MailcowManager should be invoked
        update_alias.assert_called_once()
