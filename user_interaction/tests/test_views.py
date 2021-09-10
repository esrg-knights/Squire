from django.contrib.auth.models import User
from django.test import TestCase

from core.forms import LoginForm
from utils.testing.view_test_utils import ViewValidityMixin

from user_interaction.views import HomeNonAuthenticatedView, HomeUsersView


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
