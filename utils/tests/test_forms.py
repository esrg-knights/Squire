from django import forms
from django.contrib.admin import ModelAdmin, AdminSite
from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.forms.models import model_to_dict
from django.test import TestCase, RequestFactory

from unittest.mock import MagicMock

from utils.forms import (
    FieldsetAdminFormMixin,
    RequestUserToFormModelAdminMixin,
    UpdatingUserFormMixin,
    get_basic_filter_by_field_form,
    FormGroup,
)
from utils.testing import FormValidityMixin

User = get_user_model()


class TestBasicFilterForm(FormValidityMixin, TestCase):
    def setUp(self):
        Group.objects.create(name="Test group 2")
        Group.objects.create(name="A test state")
        Group.objects.create(name="Test group 1")
        Group.objects.create(name="some other group")

        self.form_class = get_basic_filter_by_field_form("name")

    def test_filtering(self):
        self.assertEqual(self.filter_for("group").count(), 3)
        self.assertEqual(self.filter_for("up 1").count(), 1)

    def test_case_insensitive(self):
        self.assertEqual(self.filter_for("test").count(), 3)

    def test_ordering(self):
        self.assertEqual(self.filter_for("test").first().name, "A test state")

    def filter_for(self, search_string):
        """Returns a form-filtered queryset of the Groups for given search_string"""
        form = self.form_class({"search_field": search_string})
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
    """Tests for UpdatingUserFormMixin"""

    def setUp(self):
        self.initial_user = User.objects.create(username="initial_user")
        self.new_user = User.objects.create(username="new_user")

        # Use an Admin-panel LogEntry object to test (it has a FK to user)
        self.obj = LogEntry.objects.create(user=self.initial_user, action_flag=ADDITION, object_repr="My new object")

    def test_field_updates(self):
        """Tests if the user does not change before saving, and is updated after saving"""
        form = DummyForm(model_to_dict(self.obj), instance=self.obj, user=self.new_user)

        # Initial user is unchanged
        self.assertEqual(form["user"].value(), self.initial_user.id)
        self.assertEqual(LogEntry.objects.get(id=self.obj.id).user, self.initial_user)
        self.assertTrue(form.is_valid())

        # User changes after update
        form.save()
        self.assertEqual(LogEntry.objects.get(id=self.obj.id).user, self.new_user)

    def test_field_sanity_check(self):
        """Tests if an AssertionError is raised if the Form does not have updating_user_field_name"""

        class DummyForm2(DummyForm):
            updating_user_field_name = "foo"

        with self.assertRaisesMessage(
            AssertionError, "<class 'django.contrib.admin.models.LogEntry'> has no field foo"
        ):
            DummyForm2(model_to_dict(self.obj), instance=self.obj, user=self.new_user)


class DummyModelAdmin(RequestUserToFormModelAdminMixin, ModelAdmin):
    """Dummy Modeladmin for testing RequestUserToFormModelAdminMixin"""

    form = DummyForm


class RequestUserToFormMixinTest(TestCase):
    """Tests for RequestUserToFormModelAdminMixin"""

    def setUp(self):
        self.user = User.objects.create(username="test_user")

        # Use an Admin-panel LogEntry object to test (it has a FK to user)
        self.obj = LogEntry.objects.create(user=self.user, action_flag=ADDITION, object_repr="My new object")

        # Create a request
        self.factory = RequestFactory()
        self.request = self.factory.get("/testurl/")
        self.request.user = self.user

    def test_model_admin_form_has_request_user(self):
        """Tests if the ModelAdmin's form's user is set to the requesting user"""
        # The form must have the user
        model_admin = DummyModelAdmin(model=LogEntry, admin_site=AdminSite())
        form = model_admin.get_form(self.request)()
        self.assertEqual(form.user, self.user)


class FormGroupTestCase(TestCase):
    def setUp(self):
        self.form_group = self._construct_form_group(data={})

    def _construct_form_group(self, **kwargs):
        class FakeFormGroup(FormGroup):
            form_class = MagicMock()
            formset_class = MagicMock()

        FakeFormGroup.form_class.__name__ = "FakeForm"
        FakeFormGroup.formset_class.__name__ = "FakeFormSet"

        return FakeFormGroup(**kwargs)

    def test_is_valid(self):
        self.form_group.form.is_valid.return_value = False
        self.form_group.formsets[0].is_valid.return_value = True
        self.assertEqual(self.form_group.is_valid(), False)

        self.form_group.form.is_valid.return_value = True
        self.form_group.formsets[0].is_valid.return_value = False
        self.assertEqual(self.form_group.is_valid(), False)

        self.form_group.form.is_valid.return_value = True
        self.form_group.formsets[0].is_valid.return_value = True
        self.assertEqual(self.form_group.is_valid(), True)

    def test_save(self):
        self.form_group.save()
        self.form_group.form.save.assert_called_once()
        self.form_group.formsets[0].save.assert_called_once()

    def test_init_kwargs_form(self):
        """Test form init kwargs being passed correctly"""
        form_group = self._construct_form_group(
            data={"name": "attr"},
            files="files",
            auto_id=False,
            error_class="none",
            renderer="base_renderer",
            fake_kwarg="Not-auto-transfered",
        )
        call_args = form_group.form_class.call_args
        self.assertEqual(call_args.kwargs["data"], {"name": "attr"})
        self.assertEqual(call_args.kwargs["files"], "files")
        self.assertEqual(call_args.kwargs["auto_id"], False)
        self.assertEqual(call_args.kwargs["error_class"], "none")
        self.assertEqual(call_args.kwargs["renderer"], "base_renderer")
        self.assertNotIn("fake_kwarg", call_args.kwargs.keys())

    def test_init_kwargs_formset(self):
        """Test form init kwargs being passed correctly"""
        form_group = self._construct_form_group(
            data={"name": "attr"},
            files="files",
            auto_id=False,
            error_class="none",
            renderer="base_renderer",
            fake_kwarg="Not-auto-transfered",
        )
        call_args = form_group.formset_class.call_args
        self.assertEqual(call_args.kwargs["data"], {"name": "attr"})
        self.assertEqual(call_args.kwargs["files"], "files")
        self.assertEqual(call_args.kwargs["auto_id"], False)
        self.assertEqual(call_args.kwargs["error_class"], "none")
        self.assertNotIn("renderer", call_args.kwargs.keys())  # Formsets do not accept a renderer
        self.assertNotIn("fake_kwarg", call_args.kwargs.keys())

    def test_form_prefix(self):
        form_group = self._construct_form_group()
        self.assertEqual(form_group.form_class.call_args.kwargs["prefix"], "main")
        form_group = self._construct_form_group(prefix="Group")
        self.assertEqual(form_group.form_class.call_args.kwargs["prefix"], "Group-main")

    def test_formset_prefix(self):
        form_group = self._construct_form_group()
        self.assertEqual(form_group.formset_class.call_args.kwargs["prefix"], "formset")
        form_group = self._construct_form_group(prefix="Group")
        self.assertEqual(form_group.formset_class.call_args.kwargs["prefix"], "Group-formset")


class FieldsetAdminUserForm(FieldsetAdminFormMixin, forms.ModelForm):
    """ModelForm that includes fieldsets."""

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "last_login")

        fieldsets = [
            (None, {"fields": [("username",), "email", "last_login"]}),
            ("Name", {"fields": [("first_name", "last_name")]}),
        ]


class FieldsetAdminFormMixinTestCase(TestCase):
    """Tests for forms utilising FieldsetAdminFormMixin"""

    class FieldAdminForm(FieldsetAdminFormMixin, forms.ModelForm):
        """ModelForm without fieldsets."""

        class Meta:
            model = User
            fields = ("username", "first_name", "last_name", "email")

        class Media:
            css = {"all": ("extra-css-file.css",)}
            js = ("extra-js-file.js",)

    class NoMetaForm(FieldAdminForm, forms.ModelForm):
        """ModelForm without a Meta class"""

    def test_media(self):
        """Tests if form media is added and merged correctly"""
        media = FieldsetAdminFormMixinTestCase.FieldAdminForm().media.render()
        # Additional media is there
        self.assertIn("extra-js-file.js", media)
        self.assertIn("extra-css-file.css", media)
        # Parent media is there
        self.assertIn("admin/js/admin/RelatedObjectLookups.js", media)

    def test_fieldsets(self):
        """Tests whether fieldsets are properly created"""
        # Meta has fieldsets
        form = FieldsetAdminUserForm()
        fieldsets = form.get_fieldsets(None)
        self.assertEqual(len(fieldsets), 2)
        self.assertEqual(fieldsets[1][0], "Name")

        # Meta has no fieldsets (all fields are added to a single fieldset)
        form = FieldsetAdminFormMixinTestCase.FieldAdminForm()
        fieldsets = form.get_fieldsets(None)
        self.assertEqual(len(fieldsets), 1)
        name, attrs = fieldsets[0]
        self.assertIsNone(name)
        self.assertIn("fields", attrs)
        self.assertDictEqual(attrs["fields"], form.fields)

    def test_meta(self):
        """Tests whether the _meta.fieldsets attribute is set"""
        # No Meta class
        form = FieldsetAdminFormMixinTestCase.NoMetaForm()
        self.assertTrue(hasattr(form._meta, "fieldsets"))
        self.assertIsNone(form._meta.fieldsets)

        # Meta class (no fieldset attribute)
        form = FieldsetAdminFormMixinTestCase.FieldAdminForm()
        self.assertTrue(hasattr(form._meta, "fieldsets"))
        self.assertIsNone(form._meta.fieldsets)

        # Meta class (fieldset attribute)
        form = FieldsetAdminUserForm()
        self.assertTrue(hasattr(form._meta, "fieldsets"))
        self.assertIsNotNone(form._meta.fieldsets)
