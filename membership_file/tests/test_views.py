from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.template.response import TemplateResponse
from django.test import TestCase
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, TemplateView
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from dynamic_preferences.registries import global_preferences_registry

from core.tests.util import suppress_warnings, DynamicRegistryUsageMixin
from membership_file.forms import ContinueMembershipForm
from membership_file.models import Member, MemberYear, Room
from membership_file.views import (
    ExtendMembershipView,
    ExtendMembershipSuccessView,
    LinkMembershipConfirmView,
    LinkMembershipLoginView,
    LinkMembershipRegisterView,
    RegisterNewMemberAdminView,
)
from utils.testing.view_test_utils import ViewValidityMixin

global_preferences = global_preferences_registry.manager()
User = get_user_model()


class ExtendMembershipViewTest(ViewValidityMixin, DynamicRegistryUsageMixin, TestCase):
    fixtures = ["test_users", "test_members"]
    base_user_id = 100

    def setUp(self):
        global_preferences = global_preferences_registry.manager()
        global_preferences["membership__signup_year"] = MemberYear.objects.get(id=3)
        super(ExtendMembershipViewTest, self).setUp()

    def get_base_url(self, content_type=None, item_id=None):
        return reverse("membership:continue_membership")

    def test_class(self):
        self.assertTrue(issubclass(ExtendMembershipView, FormView))
        self.assertEqual(ExtendMembershipView.template_name, "membership_file/extend_membership.html")
        self.assertEqual(ExtendMembershipView.form_class, ContinueMembershipForm)
        self.assertEqual(ExtendMembershipView.success_url, reverse("membership:continue_success"))

    def test_successful_get(self):
        self.assertValidGetResponse()

    def test_succesful_post(self):
        response = self.client.post(self.get_base_url(), data={}, follow=True)
        self.assertRedirects(response, reverse("membership:continue_success"))
        msg = "Successfully extended Knights membership into {year}".format(year=MemberYear.objects.get(id=3))
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
        return reverse("membership:continue_success")

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


class RegisterNewMemberAdminViewTestCase(ViewValidityMixin, TestCase):
    """Tests for RegisterNewMemberAdminView"""

    fixtures = ["test_users"]
    base_url = reverse_lazy("admin:membership_file_member_actions", kwargs={"tool": "register_new_member"})
    base_user_id = 4
    permission_required = "membership_file.add_member"
    form_context_name = "adminform"

    def setUp(self):
        self.data = {
            "first_name": "First",
            "tussenvoegsel": "",
            "last_name": "Last",
            "legal_name": "First Last",
            "student_number": "",
            "educational_institution": "",
            "tue_card_number": "",
            "email": "user@example.com",
            "phone_number": "+311234567890",
            "street": "Dorpsstraat",
            "house_number": "1",
            "house_number_addition": "",
            "postal_code": "1234 AB",
            "city": "Eindhoven",
            "country": "The Netherlands",
            "date_of_birth": "1970-01-01",
            "notes": "",
        }
        return super().setUp()

    def test_registration_access(self):
        """Tests if the view is only accessible to those with membership_file.add_member"""
        self.assertRequiresPermission("membership_file.add_member")

    def test_successful_get(self):
        res = self.assertValidGetResponse()

    def test_messages(self):
        """Tests messages and urls they contain"""
        # With registration mail
        data = {**self.data, "do_send_registration_email": True}
        res = self.assertValidPostResponse(data=data, redirect_url=self.base_url)
        member = Member.objects.filter(email=self.data["email"]).first()
        self.assertIsNotNone(member, "New member should've been created.")
        self.assertHasMessage(
            res, messages.SUCCESS, reverse(f"admin:membership_file_member_change", args=(member.id,))
        )
        member.delete()

        # Without registration mail
        data = {**self.data, "do_send_registration_email": False}
        res = self.assertValidPostResponse(data=data, redirect_url=self.base_url)
        member = Member.objects.filter(email=self.data["email"]).first()
        self.assertIsNotNone(member, "New member should've been created.")
        self.assertHasMessage(
            res, messages.WARNING, reverse(f"admin:membership_file_member_change", args=(member.id,))
        )

    def test_admin_log(self):
        """Tests if an admin log entry is created"""
        Room.objects.create(name="Room", access_type=Room.ACCESS_OTHER)
        data = {**self.data, "do_send_registration_email": True}
        res = self.assertValidPostResponse(data=data, redirect_url=self.base_url)
        logs = LogEntry.objects.all()
        self.assertEqual(len(logs), 1, "Admin log entry should've been created.")
        self.assertEqual(logs.first().user.id, self.base_user_id)
        self.assertEqual(logs.first().object_id, str(Member.objects.filter(email=self.data["email"]).first().id))


class ResendRegistrationEmailAdminViewTestCase(ViewValidityMixin, TestCase):
    """Tests for ResendRegistrationMailAdminView"""

    fixtures = ["test_users"]
    base_url = None
    base_user_id = 4
    permission_required = ("membership_file.add_member", "membership_file.view_member")
    form_context_name = "adminform"

    def setUp(self):
        self.member = Member.objects.create(first_name="Foo", last_name="", legal_name="Foo", email="foo@example.com")
        return super().setUp()

    def get_base_url(self):
        return reverse(
            "admin:membership_file_member_actions", kwargs={"pk": self.member.id, "tool": "resend_verification"}
        )

    @suppress_warnings
    def test_resend_access(self):
        """Tests if the view is only accessible if certain conditions are met"""
        # Permission membership_file.add_member
        self.assertRequiresPermission("membership_file.add_member")

        # Already has an associated member
        self.member.user = self.user
        self.member.save()
        res = self.client.get(self.get_base_url())
        self.assertEqual(res.status_code, 400)

    def test_successful_get(self):
        res = self.assertValidGetResponse()

    def test_messages(self):
        """Tests messages and urls they contain"""
        url = reverse(f"admin:membership_file_member_change", args=(self.member.id,))
        res = self.assertValidPostResponse(redirect_url=url)
        self.assertHasMessage(
            res, messages.SUCCESS, reverse(f"admin:membership_file_member_change", args=(self.member.id,))
        )


class LinkMembershipConfirmViewTestCase(ViewValidityMixin, TestCase):
    """
    Tests related to the various views concerning membership link confirmation
    Token validity checks are already tested in utils.tests.test_tokens
    """

    fixtures = ["test_users"]
    base_url = ""
    base_user_id = None

    def setUp(self) -> None:
        super().setUp()

        self.member_to_link = Member.objects.create(
            first_name="Foo", last_name="", legal_name="Foo", email="foo@example.com"
        )
        m64 = urlsafe_base64_encode(force_bytes(self.member_to_link.pk))
        self.token_generator = LinkMembershipConfirmView.token_generator
        self._regenerate_token(update_session=False)

        # Shortcuts
        self.confirm_url = reverse("membership:link_account/confirm", args=(m64, self.token))
        self.login_url = reverse("membership:link_account/login", args=(m64,))
        self.register_url = reverse("membership:link_account/register", args=(m64,))
        self.membership_url = reverse("account:membership:view")

    def _regenerate_token(self, update_session=True):
        """Generates a token"""
        self.token = self.token_generator.make_token(self.member_to_link)

        if update_session:
            # Store token in session
            session = self.client.session
            session[LinkMembershipConfirmView.session_token_name] = self.token
            session.save()

    def test_redirect_valid(self):
        """Tests redirection if membership can still be linked"""
        # Redirect to Register page (user is not logged in)
        res = self.client.get(self.confirm_url, follow=True)
        self.assertRedirects(res, self.register_url)

        # Redirect to Login page (user IS logged in)
        self.client.force_login(User.objects.get(id=1))
        res = self.client.get(self.confirm_url, follow=True)
        self.assertRedirects(res, self.login_url)

    @suppress_warnings
    def test_redirect_invalid(self):
        """Tests redirection if membership cannot be linked"""
        # Member is already linked to (another) user
        self.member_to_link.user = User.objects.get(id=1)
        self.member_to_link.save()
        self._regenerate_token()
        res = self.client.get(self.confirm_url)
        self.assertTemplateUsed(res, LinkMembershipConfirmView.fail_template_name)
        res = self.client.get(self.login_url)
        self.assertTemplateUsed(res, LinkMembershipLoginView.fail_template_name)
        res = self.client.get(self.register_url)
        self.assertTemplateUsed(res, LinkMembershipRegisterView.fail_template_name)

        # User is logged in but accesses the register page
        Member.objects.update(user=None)
        self._regenerate_token()
        user = User.objects.get(id=2)
        self.client.force_login(user)
        res = self.client.get(self.register_url)
        self.assertTemplateUsed(res, LinkMembershipRegisterView.fail_template_name)

        # User is already linked to another member
        Member.objects.create(first_name="Bar", last_name="", legal_name="Bar", email="bar@example.com", user=user)
        res = self.client.get(self.confirm_url)
        self.assertTemplateUsed(res, LinkMembershipConfirmView.fail_template_name)
        res = self.client.get(self.login_url)
        self.assertTemplateUsed(res, LinkMembershipLoginView.fail_template_name)
        res = self.client.get(self.register_url)
        self.assertTemplateUsed(res, LinkMembershipRegisterView.fail_template_name)

    def test_context(self):
        """Tests whether the correct context variables are passed around"""
        self._regenerate_token()
        # User is not logged in
        res: TemplateResponse = self.assertValidGetResponse(url=self.login_url)
        self.assertTemplateNotUsed(res, LinkMembershipLoginView.fail_template_name)
        self.assertIsInstance(res, TemplateResponse)
        self.assertEqual(res.context_data.get("register_url"), self.register_url)

        res: TemplateResponse = self.assertValidGetResponse(url=self.register_url)
        self.assertTemplateNotUsed(res, LinkMembershipRegisterView.fail_template_name)
        self.assertIsInstance(res, TemplateResponse)
        self.assertEqual(res.context_data.get("login_url"), self.login_url)

        # User IS logged in (do not give the option to register)
        self.client.force_login(User.objects.get(id=1))
        res: TemplateResponse = self.assertValidGetResponse(url=self.login_url)
        self.assertTemplateNotUsed(res, LinkMembershipLoginView.fail_template_name)
        self.assertIsInstance(res, TemplateResponse)
        self.assertIsNone(res.context_data.get("register_url"))

    def test_login_valid(self):
        """Tests behaviour if a login succeeds"""
        self._regenerate_token()
        data = {"username": "newuser", "password": "linkedlogintest"}
        user = User.objects.create_user(**data)
        res: TemplateResponse = self.assertValidPostResponse(data, self.login_url, self.membership_url)
        self.assertTemplateNotUsed(res, LinkMembershipLoginView.fail_template_name)
        self.assertIsInstance(res, TemplateResponse)
        # User is linked to member
        self.member_to_link.refresh_from_db()
        self.assertEqual(self.member_to_link.user, user)
        self.assertEqual(self.member_to_link.last_updated_by, user)
        self.assertHasMessage(res, messages.SUCCESS)

        # Session token should be deleted
        self.assertNotIn(LinkMembershipConfirmView.session_token_name, self.client.session)

    def test_login_already_member(self):
        """Tests behaviour if a user logs in that is already linked to a member"""
        self._regenerate_token()
        data = {"username": "newuser", "password": "linkedlogintest"}
        user = User.objects.create_user(**data)
        member = Member.objects.create(
            first_name="Bar", last_name="", legal_name="Bar", email="bar@example.com", user=user
        )
        res: TemplateResponse = self.assertValidPostResponse(data, self.login_url)
        self.assertTemplateNotUsed(res, LinkMembershipLoginView.fail_template_name)
        self.assertIsInstance(res, TemplateResponse)
        # User is not linked to the member
        self.member_to_link.refresh_from_db()
        self.assertIsNone(self.member_to_link.user)
        self.assertIsNone(self.member_to_link.last_updated_by, user)
        self.assertHasMessage(res, messages.ERROR)

        # Session data kept intact
        self.assertTrue(res.wsgi_request.user.is_anonymous)
        self.assertIn(LinkMembershipConfirmView.session_token_name, self.client.session)
        self.assertEqual(self.client.session[LinkMembershipConfirmView.session_token_name], self.token)

    def test_registration_valid(self):
        """Tests behaviour if registration succeeds"""
        self._regenerate_token()
        data = {"username": "newuser", "password1": "linkedlogintest", "password2": "linkedlogintest"}
        res: TemplateResponse = self.assertValidPostResponse(data, self.register_url, self.membership_url)
        self.assertTemplateNotUsed(res, LinkMembershipRegisterView.fail_template_name)
        self.assertIsInstance(res, TemplateResponse)
        # User is auto-logged-in and linked to member
        user = User.objects.filter(username="newuser").first()
        self.assertIsNotNone(user)
        self.assertEqual(res.wsgi_request.user.username, user.username)
        self.member_to_link.refresh_from_db()
        self.assertEqual(self.member_to_link.user, user)
        self.assertEqual(self.member_to_link.last_updated_by, user)
        self.assertHasMessage(res, messages.SUCCESS)

        # Session token should be deleted
        self.assertNotIn(LinkMembershipConfirmView.session_token_name, self.client.session)
