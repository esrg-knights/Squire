from django.contrib import messages
from django.test import TestCase
from django.urls import reverse
from django.views.generic import FormView, TemplateView

from dynamic_preferences.registries import global_preferences_registry

global_preferences = global_preferences_registry.manager()

from core.tests.util import suppress_warnings, DynamicRegistryUsageMixin
from utils.testing.view_test_utils import ViewValidityMixin
from membership_file.forms import ContinueMembershipForm
from membership_file.models import MemberYear
from membership_file.views import ExtendMembershipView, ExtendMembershipSuccessView


class ExtendMembershipViewTest(ViewValidityMixin, DynamicRegistryUsageMixin, TestCase):
    fixtures = ["test_users", "test_members"]
    base_user_id = 100

    def setUp(self):
        global_preferences = global_preferences_registry.manager()
        global_preferences["membership__signup_year"] = MemberYear.objects.get(id=3)
        super(ExtendMembershipViewTest, self).setUp()

    def get_base_url(self, content_type=None, item_id=None):
        return reverse("membership_file/continue_membership")

    def test_class(self):
        self.assertTrue(issubclass(ExtendMembershipView, FormView))
        self.assertEqual(ExtendMembershipView.template_name, "membership_file/extend_membership.html")
        self.assertEqual(ExtendMembershipView.form_class, ContinueMembershipForm)
        self.assertEqual(ExtendMembershipView.success_url, reverse("membership_file/continue_success"))

    def test_successful_get(self):
        self.assertValidGetResponse()

    def test_succesful_post(self):
        response = self.client.post(self.get_base_url(), data={}, follow=True)
        self.assertRedirects(response, reverse("membership_file/continue_success"))
        msg = "Succesfully extended Knights membership into {year}".format(year=MemberYear.objects.get(id=3))
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)

    @suppress_warnings
    def test_disabled_signups(self):
        global_preferences = global_preferences_registry.manager()
        global_preferences["membership__signup_year"] = None
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 403)


class ExtendMembershipSuccessViewTest(ViewValidityMixin, DynamicRegistryUsageMixin, TestCase):
    fixtures = ["test_users", "test_members"]
    base_user_id = 100

    def setUp(self):
        global_preferences["membership__signup_year"] = MemberYear.objects.get(id=3)
        super(ExtendMembershipSuccessViewTest, self).setUp()

    def get_base_url(self, content_type=None, item_id=None):
        return reverse("membership_file/continue_success")

    def test_class(self):
        self.assertTrue(issubclass(ExtendMembershipSuccessView, TemplateView))
        self.assertEqual(
            ExtendMembershipSuccessView.template_name, "membership_file/extend_membership_successpage.html"
        )

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    @suppress_warnings
    def test_disabled_signups(self):
        global_preferences["membership__signup_year"] = None
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 403)
