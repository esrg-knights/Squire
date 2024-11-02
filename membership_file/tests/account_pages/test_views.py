from django.test import TestCase
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse
from django.views.generic import UpdateView

from dynamic_preferences.registries import global_preferences_registry

global_preferences = global_preferences_registry.manager()

from core.util import get_permission_objects_from_string
from user_interaction.accountcollective import AccountViewMixin
from utils.testing.view_test_utils import ViewValidityMixin

from membership_file.forms import MemberForm
from membership_file.models import Member, MemberYear
from membership_file.util import MembershipRequiredMixin
from membership_file.account_pages.views import MembershipDataView, MembershipChangeView


class MembershipDataViewTestCase(ViewValidityMixin, TestCase):
    """
    Tests the MembershipDataView class
    """

    fixtures = ["test_users", "test_members.json"]
    base_user_id = 100

    def setUp(self):
        super(MembershipDataViewTestCase, self).setUp()
        self.user.user_permissions.add(
            *list(get_permission_objects_from_string([MembershipDataView.permission_required]))
        )

    def test_class(self):
        self.assertTrue(issubclass(MembershipDataView, AccountViewMixin))
        self.assertEqual(MembershipDataView.model, Member)
        self.assertEqual(MembershipDataView.template_name, "membership_file/membership_view.html")

    def test_permission_required(self):
        """Tests that the agreed upon permissions are requiered"""
        # No need to simulate, we can trust on PermissionRequiredMixin
        self.assertTrue(issubclass(MembershipDataView, PermissionRequiredMixin))
        self.assertEqual(
            MembershipDataView.permission_required, "membership_file.can_view_membership_information_self"
        )

    def test_successful_get(self):
        response = self.client.get(reverse("account:membership:view"), data={})
        self.assertEqual(response.status_code, 200)

    def test_context_data(self):
        response = self.client.get(reverse("account:membership:view"), data={})
        self.assertNotIn("sign_up_message", response.context)
        self.assertIn("memberyears", response.context)
        self.assertIn("activeyears", response.context)
        self.assertEqual(len(response.context["activeyears"]), 1)
        self.assertEqual(response.context["activeyears"][0].id, 1)

    def test_continue_membership_message(self):
        year = MemberYear.objects.get(id=3)
        global_preferences["membership__signup_year"] = year
        response = self.client.get(reverse("account:membership:view"), data={})
        self.assertIn("sign_up_message", response.context)
        msg = response.context["sign_up_message"]
        self.assertIn("msg_text", msg)
        self.assertIn("btn_text", msg)
        self.assertEqual(msg["msg_type"], "info")
        self.assertEqual(msg["btn_url"], reverse("membership:continue_membership"))


class MembershipChangeViewTestCase(ViewValidityMixin, TestCase):
    """
    Tests the MembershipDataView class
    """

    fixtures = ["test_users", "test_members.json"]
    base_user_id = 100

    def setUp(self):
        super(MembershipChangeViewTestCase, self).setUp()

        self.member = Member.objects.get(id=1)
        self.form_data = {
            "legal_name": self.member.legal_name,
            "first_name": self.member.first_name,
            "tussenvoegsel": self.member.tussenvoegsel,
            "last_name": self.member.last_name,
            "date_of_birth": self.member.date_of_birth,
            "email": self.member.email,
            "street": self.member.street,
            "house_number": self.member.house_number,
            "city": self.member.city,
            "country": self.member.country,
            "educational_institution": self.member.educational_institution,
            "student_number": self.member.student_number,
            "tue_card_number": self.member.tue_card_number,
        }

    def test_class(self):
        self.assertTrue(issubclass(MembershipChangeView, MembershipRequiredMixin))
        self.assertTrue(issubclass(MembershipChangeView, AccountViewMixin))
        self.assertTrue(issubclass(MembershipChangeView, UpdateView))
        self.assertEqual(MembershipChangeView.form_class, MemberForm)
        self.assertEqual(MembershipChangeView.template_name, "membership_file/membership_edit.html")
        self.assertEqual(MembershipChangeView.success_url, reverse("account:membership:view"))

    def test_permission_required(self):
        """Tests that the agreed upon permissions are required"""
        # No need to simulate, we can trust on PermissionRequiredMixin
        self.assertTrue(issubclass(MembershipDataView, PermissionRequiredMixin))
        self.assertIn("membership_file.can_view_membership_information_self", MembershipChangeView.permission_required)
        self.assertIn(
            "membership_file.can_change_membership_information_self", MembershipChangeView.permission_required
        )

    def test_successful_get(self):
        self.user.user_permissions.add(
            *list(get_permission_objects_from_string(MembershipChangeView.permission_required))
        )
        response = self.client.get(reverse("account:membership:edit"), data={})
        self.assertEqual(response.status_code, 200)

    def test_valid_post(self):
        self.user.user_permissions.add(
            *list(get_permission_objects_from_string(MembershipChangeView.permission_required))
        )
        self.assertValidPostResponse(
            {
                **self.form_data,
                "house_number": 69,
            },
            url=reverse("account:membership:edit"),
            redirect_url=reverse("account:membership:view"),
            fetch_redirect_response=False,
        )
        self.member.refresh_from_db()
        self.assertEqual(self.member.house_number, 69)
