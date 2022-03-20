from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.test import TestCase
from django.urls import reverse
from django.views.generic import TemplateView, FormView, UpdateView

from core.forms import PasswordChangeForm
from user_interaction.account_pages.views import *
from utils.testing.view_test_utils import ViewValidityMixin
from user_interaction.accountcollective import AccountViewMixin
from membership_file.models import Member


class AccountViewPageTestCase(ViewValidityMixin, TestCase):
    fixtures = ['test_users']
    base_user_id = 1

    def test_class(self):
        self.assertTrue(issubclass(SiteAccountView, AccountViewMixin))
        self.assertTrue(issubclass(SiteAccountView, TemplateView))
        self.assertEqual(SiteAccountView.template_name, "user_interaction/account_pages/site_account_page.html")

    def test_successful_get(self):
        self.assertValidGetResponse(url=reverse('account:site_account'))


class AccountPasswordChangeTestCase(ViewValidityMixin, TestCase):
    """ Tests for general individual pages """
    fixtures = ['test_users']
    base_user_id = 1

    def get_base_url(self):
        return reverse('account:password_change')

    def test_class(self):
        self.assertTrue(issubclass(AccountPasswordChangeView, AccountViewMixin))
        self.assertTrue(issubclass(AccountPasswordChangeView, PasswordChangeView))
        self.assertEqual(AccountPasswordChangeView.template_name, "user_interaction/account_pages/password_change_form.html")
        self.assertEqual(AccountPasswordChangeView.success_url, reverse('account:site_account'))
        self.assertEqual(AccountPasswordChangeView.form_class, PasswordChangeForm)

    def test_successful_get(self):
        self.assertValidGetResponse()

    def test_post_succesful(self):
        # Set the password as the fixture is the hashed password
        old_password = "1234abcd&G"
        self.user.set_password(old_password)
        self.user.save()
        # Force login the user, it's logged out due to password change
        self.client.force_login(self.user)

        data = {
            'old_password': old_password,
            'new_password1': "1337^cc3sGAME",
            'new_password2': "1337^cc3sGAME",
        }
        self.assertValidPostResponse(
            data=data,
            redirect_url=AccountPasswordChangeView.success_url,
            fetch_redirect_response=True
        )


class LayoutPreferencesUpdateTestCase(ViewValidityMixin, TestCase):
    """ Tests for general individual pages """
    fixtures = ['test_users']
    base_user_id = 1

    def get_base_url(self):
        return reverse('account:layout_change')

    def test_class(self):
        self.assertTrue(issubclass(LayoutPreferencesUpdateView, AccountViewMixin))
        self.assertTrue(issubclass(LayoutPreferencesUpdateView, FormView))
        self.assertEqual(LayoutPreferencesUpdateView.template_name, "user_interaction/account_pages/layout_preferences_change_form.html")
        self.assertEqual(LayoutPreferencesUpdateView.success_url, reverse('account:site_account'))

    def test_successful_get(self):
        self.assertValidGetResponse()

    def test_post_succesful(self):
        data = {'layout__theme': "THEME_LIGHT"}
        self.assertValidPostResponse(
            data=data,
            redirect_url=LayoutPreferencesUpdateView.success_url
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.preferences['layout__theme'], data['layout__theme'])


class CalendarPreferencesUpdateTestCase(ViewValidityMixin, TestCase):
    """ Tests for general individual pages """
    fixtures = ['test_users', 'test_members']
    base_user_id = 100

    def get_base_url(self):
        return reverse('account:calendar_change')

    def test_class(self):
        self.assertTrue(issubclass(CalendarPreferenceView, AccountViewMixin))
        self.assertTrue(issubclass(CalendarPreferenceView, UpdateView))
        self.assertEqual(CalendarPreferenceView.template_name, "user_interaction/account_pages/calendar_preferences_change_form.html")
        self.assertEqual(CalendarPreferenceView.success_url, reverse('account:site_account'))

    def test_successful_get(self):
        self.assertValidGetResponse()

    def test_post_succesful(self):
        data = {'use_birthday': ['on']}
        self.assertValidPostResponse(
            data=data,
            redirect_url=CalendarPreferenceView.success_url
        )
        self.user.member.refresh_from_db()

        self.assertEqual(
            self.user.member.membercalendarsettings.use_birthday,
            True
        )
