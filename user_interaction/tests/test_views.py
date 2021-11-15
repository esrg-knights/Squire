from django.contrib.auth.models import User
from django.urls.base import reverse, reverse_lazy
from django.test import TestCase
from dynamic_preferences.users.forms import UserPreferenceForm

from core.forms import LoginForm
from core.tests.util import TestAccountUser, check_http_response_with_login_redirect
from user_interaction.views import HomeNonAuthenticatedView, HomeUsersView, UpdateUserPreferencesView
from utils.testing.view_test_utils import ViewValidityMixin


class TestHomePageView(ViewValidityMixin, TestCase):
    base_url = '/'

    def test_anonymoususer(self):
        # Assert response is valid and uses the correct class (soft validation through template name)
        response = self.assertValidGetResponse()
        self.assertTemplateUsed(response, HomeNonAuthenticatedView.template_name)
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], LoginForm)

    def test_authenticated_user(self):
        self.client.force_login(User.objects.create())

        response = self.assertValidGetResponse()
        self.assertTemplateUsed(response, HomeUsersView.template_name)
        self.assertIn('activities', response.context)


class TestsFrontend(TestCase):
    """ Tests for general individual pages """
    fixtures = TestAccountUser.get_fixtures()

    def test_preferences(self):
        """ Tests accessibility of the page to change user preference """
        # Account users should be able to access the page properly
        # Anonymous users should be redirected to the login page
        res, _ = check_http_response_with_login_redirect(self, reverse("user_interaction:change_preferences"), "get")

        # Ensure the correct template is used, and that the change form is present
        self.assertTemplateUsed(res, UpdateUserPreferencesView.template_name)
        self.assertIn('form', res.context)
        self.assertIsInstance(res.context['form'], UserPreferenceForm)

