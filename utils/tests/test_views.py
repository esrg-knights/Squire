from unittest.mock import MagicMock
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.admin import helpers, ModelAdmin
from django.contrib.admin.widgets import AdminTextInputWidget, AdminSplitDateTime
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.messages import constants
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import TestCase, RequestFactory
from django.views import View
from django.views.generic import ListView, FormView
from django.forms import Form, BooleanField
from utils.tests.test_forms import FieldsetAdminUserForm

User = get_user_model()


from utils.views import (
    ModelAdminFormViewMixin,
    SearchFormMixin,
    RedirectMixin,
    PostOnlyFormViewMixin,
    SuperUserRequiredMixin,
)


class TestForm(Form):
    fail_clean = BooleanField(initial=False, required=False)
    display_success_message = BooleanField(initial=False, required=False)

    def clean(self):
        if self.cleaned_data["fail_clean"] == True:
            raise ValidationError("Test error was triggered", code="testerror")
        return self.cleaned_data

    def save(self):
        pass


class TestRedirectMixin(TestCase):
    class TestView(RedirectMixin, FormView):
        success_url = "/success/"
        form_class = TestForm

    def _build_for_url(self, url, **init_kwargs):
        request = RequestFactory().get(url)

        view = self.TestView(**init_kwargs)
        view.setup(request)
        return view

    def test_succes_url_normal(self):
        # No redirect, so normal success_url needs to be used
        view = self._build_for_url("")
        url = view.get_success_url()
        self.assertEqual(url, "/success/")

    def test_succes_url_redirect(self):
        view = self._build_for_url("?redirect_to=/to_other/")
        url = view.get_success_url()
        self.assertEqual(url, "/to_other/")

    def test_redirect_url_name(self):
        url = "?on_success=/test_detour/"
        view = self._build_for_url(url, redirect_url_name="on_success")
        url = view.get_success_url()
        self.assertEqual(url, "/test_detour/")

    def test_context_data(self):
        view = self._build_for_url("?redirect_to=/test_url/")
        context = view.get_context_data()
        self.assertIn("redirect_to_url", context.keys())
        self.assertEqual(context["redirect_to_url"], "/test_url/")


class TestPostOnlyFormViewMixin(TestCase):
    class TestView(PostOnlyFormViewMixin, FormView):
        form_class = TestForm
        success_url = "/succes/"

        def get_success_message(self, form):
            if form.cleaned_data["display_success_message"]:
                return "Success triggered"
            return None

    def _build_for_url(self, url="", http_method="post", data=None, **init_kwargs):
        request = getattr(RequestFactory(), http_method)(url, data=data)

        # Requsetfactory does not support middleware, so it should be added manually
        # adding session
        get_response = MagicMock()
        middleware = SessionMiddleware(get_response)
        middleware.process_request(request)
        request.session.save()

        # adding messages
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        view = self.TestView(**init_kwargs)
        view.setup(request)
        response = view.dispatch(request)
        return response, request

    def test_get(self):
        """Tests that a get defaults back to the normal page and displays an access error"""
        response, request = self._build_for_url(http_method="get")

        self.assertEqual(response.status_code, 302)  # Test Redirect code
        self.assertEqual(response.url, self.TestView.success_url)

        self.assertEqual(self.get_first_message(request).level, constants.WARNING)

    def test_post_invalid(self):
        response, request = self._build_for_url(data={"fail_clean": True})

        self.assertEqual(response.status_code, 302)  # Test Redirect code
        self.assertEqual(response.url, self.TestView.success_url)

        message_obj = self.get_first_message(request)
        self.assertEqual(message_obj.level, constants.WARNING)
        self.assertEqual(message_obj.message, "Action could not be performed; " + "Test error was triggered")

    def test_post_valid_messageless(self):
        response, request = self._build_for_url(data={"fail_clean": False})

        self.assertEqual(response.status_code, 302)  # Test Redirect code
        self.assertEqual(response.url, self.TestView.success_url)

        self.assertEqual(len(request._messages), 0)

    def test_post_valid_message(self):
        response, request = self._build_for_url(data={"display_success_message": True})

        message_obj = self.get_first_message(request)
        self.assertEqual(message_obj.level, constants.SUCCESS)
        self.assertEqual(message_obj.message, "Success triggered")

    def get_first_message(self, request):
        """Returns the first message in the messages framework"""
        for message in request._messages:
            # This is weird, but searching with [0] provides an error. So I do this instead
            return message


class TestSearchFormMixin(TestCase):
    class TestView(SearchFormMixin, ListView):
        # Fictive view for testing the mixin
        model = Group
        filter_field_name = "name"

    def setUp(self):
        Group.objects.create(name="Test group 2")
        Group.objects.create(name="A test state")
        Group.objects.create(name="Test group 1")
        Group.objects.create(name="some other group")

        self.request = RequestFactory().get("?search_field=group")

        self.view = self.TestView()
        self.view.setup(self.request)
        self.response = self.view.dispatch(self.request)

    def test_get_filter_form(self):
        form = self.view.get_filter_form()
        self.assertEqual(form.__class__.__name__, "FilterByFieldForm")

    def test_context_data(self):
        context = self.view.get_context_data()
        self.assertIn("filter_form", context.keys())
        self.assertEqual(context["filter_form"], self.view.search_form)

    def test_get_queryset(self):
        self.assertEqual(self.view.get_queryset().count(), 3)


class TestSuperUserRequiredMixin(TestCase):
    """Tests whether only superusers can access views with this Mixin"""

    class TestView(SuperUserRequiredMixin, View):
        def get(self, *args, **kwargs):
            return HttpResponse()

    def setUp(self):
        self.admin = User.objects.create(username="admin", is_superuser=True)
        self.staff = User.objects.create(username="staff", is_staff=True)
        self.user = User.objects.create(username="user")

        self.request = RequestFactory().get("")
        self.view = self.TestView.as_view()

    def test_admin_access(self):
        """Admins can access the view"""
        self.request.user = self.admin
        res = self.view(self.request)
        self.assertEqual(res.status_code, 200)

    def test_user_denied(self):
        """Normal users cannot access the view"""
        self.request.user = self.user
        with self.assertRaises(PermissionDenied):
            self.view(self.request)

    def test_staff_denied(self):
        """Staff cannot access the view"""
        self.request.user = self.staff
        with self.assertRaises(PermissionDenied):
            self.view(self.request)


class ModelAdminFormViewMixinTestCase(TestCase):
    """Tests for ModelAdminFormViewMixin"""

    class DummyModelFormView(ModelAdminFormViewMixin, FormView):
        """FormView in combination with FieldsetAdminUserForm"""

        form_class = FieldsetAdminUserForm
        template_name = "utils/testing/test_mixin_template.html"

    view_class = DummyModelFormView

    def setUp(self) -> None:
        self.model_admin = ModelAdmin(model=User, admin_site=AdminSite())
        self.view = self.view_class(model_admin=self.model_admin)
        request_factory = RequestFactory()
        req = request_factory.get(f"/my_path/")
        req.user = User.objects.create(username="admin", is_superuser=True)
        self.view.setup(req)
        self.view.object = None

        return super().setUp()

    def test_admin_widgets(self):
        """Tests whether admin widgets properly replace standard widgets. E.g. AdminSplitDateTime"""
        context = self.view.get_context_data()
        self.assertIsInstance(context.get("adminform", None), helpers.AdminForm)
        adminform: helpers.AdminForm = context["adminform"]
        form = adminform.form
        # Form fields should be converted to admin classes
        self.assertIsInstance(form.fields["username"].widget, AdminTextInputWidget)
        self.assertIsInstance(form.fields["last_login"].widget, AdminSplitDateTime)

        # More context needed for template
        self.assertTrue(context.get("is_nav_sidebar_enabled", False))
        self.assertIsNotNone(context.get("opts", None))
        self.assertIn("title", context)
