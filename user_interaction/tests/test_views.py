from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from dynamic_preferences.registries import global_preferences_registry

global_preferences = global_preferences_registry.manager()

from core.forms import LoginForm
from core.tests.util import DynamicRegistryUsageMixin
from user_interaction.views import HomeNonAuthenticatedView, HomeUsersView
from utils.testing.view_test_utils import ViewValidityMixin
from membership_file.models import MemberYear


class TestHomePageView(ViewValidityMixin, DynamicRegistryUsageMixin, TestCase):
    base_url = "/"

    def test_anonymoususer(self):
        # Assert response is valid and uses the correct class (soft validation through template name)
        response = self.assertValidGetResponse()
        self.assertTemplateUsed(response, HomeNonAuthenticatedView.template_name)
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], LoginForm)

    def test_authenticated_user(self):
        self.client.force_login(User.objects.create())

        response = self.assertValidGetResponse()
        self.assertTemplateUsed(response, HomeUsersView.template_name)
        self.assertIn("activities", response.context)

    def test_home_page_message(self):
        # Set environment variables
        global_preferences["homepage__home_page_message"] = "Here is a message"

        self.client.force_login(User.objects.create())
        msg = self.assertValidGetResponse().context["unique_messages"][0]

        self.assertIn("msg_text", msg)
        self.assertEqual(msg["msg_type"], "info")

    def test_home_page_extend_membership_message(self):
        # Set environment variables
        global_preferences["membership__signup_year"] = MemberYear.objects.create(name="current year")

        self.client.force_login(User.objects.create())
        msg = self.assertValidGetResponse().context["unique_messages"][0]

        self.assertIn("msg_text", msg)
        self.assertIn("btn_text", msg)
        self.assertEqual(msg["msg_type"], "info")
        self.assertEqual(msg["btn_url"], reverse("membership:continue_membership"))
