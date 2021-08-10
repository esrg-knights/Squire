from django import forms
from django.contrib.admin import ModelAdmin, AdminSite
from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.forms.models import model_to_dict
from django.test import TestCase, RequestFactory

from utils.forms import RequestUserToFormModelAdminMixin, UpdatingUserFormMixin, get_basic_filter_by_field_form
from utils.testing import FormValidityMixin

User = get_user_model()

class TestBasicFilterForm(FormValidityMixin, TestCase):

    def setUp(self):
        Group.objects.create(name="Test group 2")
        Group.objects.create(name="A test state")
        Group.objects.create(name="Test group 1")
        Group.objects.create(name="some other group")

        self.form_class = get_basic_filter_by_field_form('name')

    def test_filtering(self):
        self.assertEqual(self.filter_for('group').count(), 3)
        self.assertEqual(self.filter_for('up 1').count(), 1)

    def test_case_insensitive(self):
        self.assertEqual(self.filter_for('test').count(), 3)

    def test_ordering(self):
        self.assertEqual(self.filter_for('test').first().name, "A test state")

    def filter_for(self, search_string):
        """ Returns a form-filtered queryset of the Groups for given search_string """
        form = self.form_class({'search_field': search_string})
        if form.is_valid():
            return form.get_filtered_items(Group.objects.all())
        raise AssertionError("Somehow form was not deemed valid?")


class DummyForm(UpdatingUserFormMixin, forms.ModelForm):
    """
        Modelform for Django's LogEntry model. Used for testing UpdatingUserFormMixin.
    """
    class Meta:
        model = LogEntry
        fields = "__all__"
    updating_user_field_name = "user"

class UpdatingUserFormMixinTest(TestCase):
    """ Tests for UpdatingUserFormMixin """
    def setUp(self):
        self.initial_user = User.objects.create(username="initial_user")
        self.new_user = User.objects.create(username="new_user")

        # Use an Admin-panel LogEntry object to test (it has a FK to user)
        self.obj = LogEntry.objects.create(user=self.initial_user, action_flag=ADDITION, object_repr="My new object")

    def test_field_updates(self):
        """ Tests if the user does not change before saving, and is updated after saving """
        form = DummyForm(model_to_dict(self.obj), instance=self.obj, user=self.new_user)

        # Initial user is unchanged
        self.assertEqual(form['user'].value(), self.initial_user.id)
        self.assertEqual(LogEntry.objects.get(id=self.obj.id).user, self.initial_user)
        self.assertTrue(form.is_valid())

        # User changes after update
        form.save()
        self.assertEqual(LogEntry.objects.get(id=self.obj.id).user, self.new_user)

    def test_field_sanity_check(self):
        """ Tests if an AssertionError is raised if the Form does not have updating_user_field_name """
        class DummyForm2(DummyForm):
            updating_user_field_name = "foo"

        with self.assertRaisesMessage(AssertionError,
                "<class 'django.contrib.admin.models.LogEntry'> has no field foo"):
            DummyForm2(model_to_dict(self.obj), instance=self.obj, user=self.new_user)

class DummyModelAdmin(RequestUserToFormModelAdminMixin, ModelAdmin):
    """ Dummy Modeladmin for testing RequestUserToFormModelAdminMixin """
    form = DummyForm

class RequestUserToFormMixinTest(TestCase):
    """ Tests for RequestUserToFormModelAdminMixin """
    def setUp(self):
        self.user = User.objects.create(username="test_user")

        # Use an Admin-panel LogEntry object to test (it has a FK to user)
        self.obj = LogEntry.objects.create(user=self.user, action_flag=ADDITION, object_repr="My new object")

        # Create a request
        self.factory = RequestFactory()
        self.request = self.factory.get('/testurl/')
        self.request.user = self.user

    def test_model_admin_form_has_request_user(self):
        """ Tests if the ModelAdmin's form's user is set to the requesting user """
        # The form must have the user
        model_admin = DummyModelAdmin(model=LogEntry, admin_site=AdminSite())
        form = model_admin.get_form(self.request)()
        self.assertEqual(form.user, self.user)
