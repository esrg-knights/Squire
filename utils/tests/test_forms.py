from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group
from django.test import TestCase

from utils.forms import get_basic_filter_by_field_form
from utils.testing import FormValidityMixin


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


class TestFormValidityMixin(FormValidityMixin, TestCase):
    class TestForm(forms.Form):
        """ Fictive form for Form testing used in TestFormValidityMixin"""
        main_field = forms.CharField(required=False)
        fake_field = forms.CharField(required=False)

        def clean_main_field(self):
            if self.cleaned_data["main_field"] == "break_field":
                raise ValidationError('Test exception', code='invalid_field')
            return self.cleaned_data["main_field"]

        def clean(self):
            # Use get function, a fail in clean_main_field removes the entry from cleaned_data
            if self.cleaned_data.get('main_field', '') == "break_form":
                raise ValidationError('Test exception', code='invalid_form')
            return self.cleaned_data
    form_class = TestForm

    def raisesAssertionError(self, method_name, *args, **kwargs):
        try:
            self.__getattribute__(method_name)(*args, **kwargs)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"Assertionerror not raised on {method_name}")

    def test_assertHasField(self):
        # This should not raise an error
        self.assertHasField('main_field')
        # This should
        self.raisesAssertionError('assertHasField', 'missing_field')

    def test_assertFormValid(self):
        # This should not raise an error
        self.assertFormValid({'main_field': "ok"})
        # This should
        self.raisesAssertionError('assertFormValid', {'main_field': "break_field"})

    def test_assertFormHasError_in_field(self):
        self.assertFormHasError({'main_field': 'break_field'}, 'invalid_field')
        self.assertFormHasError({'main_field': 'break_field'}, 'invalid_field', field='main_field')

        # Error is in main_field not fake_field
        self.raisesAssertionError('assertFormHasError', {'main_field': 'break_field'}, 'invalid_form', field='fake_field')
        # This next data raises an error, just not the one with this code
        self.raisesAssertionError('assertFormHasError', {'main_field': 'break_form'}, 'invalid_field')

    def test_assertFormHasError_in_form(self):
        self.assertFormHasError({'main_field': 'break_form'}, 'invalid_form')

        # Should raise no error
        self.raisesAssertionError('assertFormHasError', {'main_field': 'break_nothing'}, 'invalid_form')
        # Error is not in main_field, but elsewhere
        self.raisesAssertionError('assertFormHasError', {'main_field': 'break_form'}, 'invalid_form', field='main_field')







