from django import forms
from django.core.exceptions import ValidationError
from django.test import TestCase


from utils.testing.form_test_util import FormValidityMixin


class TestFormValidityMixin(FormValidityMixin, TestCase):
    class TestForm(forms.Form):
        """Fictive form for Form testing used in TestFormValidityMixin"""

        main_field = forms.CharField(required=True)
        fake_field = forms.CharField(required=False)

        def clean_main_field(self):
            if self.cleaned_data["main_field"] == "break_field":
                raise ValidationError("Test field exception", code="invalid_field")
            return self.cleaned_data["main_field"]

        def clean(self):
            # Use get function, a fail in clean_main_field removes the entry from cleaned_data
            if self.cleaned_data.get("main_field", "") == "break_form":
                raise ValidationError("Test form exception", code="invalid_form")
            return self.cleaned_data

    form_class = TestForm
    longMessage = False

    def raisesAssertionError(self, method, *args, **kwargs):
        if isinstance(method, str):
            method = self.__getattribute__(method)
        try:
            method(*args, **kwargs)
        except AssertionError as error:
            return error
        else:
            raise AssertionError(f"Assertionerror not raised on {method_name}")

    def test_assertHasField(self):
        # This should not raise an error
        self.assertHasField("main_field")
        # This should
        error = self.raisesAssertionError(self.assertHasField, "missing_field")
        self.assertEqual(
            error.__str__(),
            "{field_name} was not a field in {form_class_name}".format(
                field_name="missing_field",
                form_class_name="TestForm",
            ),
        )

    def test_assertHasField_contains_property(self):
        self.raisesAssertionError(self.assertHasField, "main_field", fake_prop=True)

    def test_assertHasField_equal_property(self):
        """Tests that properties of the field can be tested"""
        # This should not raise an error
        self.assertHasField("main_field", required=True)
        # This should
        error = self.raisesAssertionError(self.assertHasField, "main_field", required=False)
        self.assertEqual(
            error.__str__(),
            "{field_name}.{key} was not '{expected_value}', but '{actual_value}' instead".format(
                field_name="main_field", key="required", expected_value=False, actual_value=True
            ),
        )

    def test_assertHasField_equal_instance(self):
        """Tests that properties of the field can be tested"""
        # This should not raise an error
        self.assertHasField("main_field", widget__class=forms.TextInput)
        # This should
        error = self.raisesAssertionError(self.assertHasField, "main_field", widget__class=forms.EmailInput)
        self.assertEqual(
            error.__str__(),
            "{field_name}.{key} was not of type '{expected_type}', but '{actual_type}' instead".format(
                field_name="main_field",
                key="widget",
                expected_type=forms.EmailInput.__name__,
                actual_type=forms.TextInput.__name__,
            ),
        )

    def test_assertFormValid(self):
        # This should not raise an error
        self.assertFormValid({"main_field": "ok"})
        # This should
        error = self.raisesAssertionError(self.assertFormValid, {"main_field": "break_field"})
        self.assertEqual(
            error.__str__(),
            "The form was not valid. At least one error was encountered: '{exception_text}' in '{location}'".format(
                exception_text="Test field exception", location="main_field"
            ),
        )

    def test_assertFormHasError_in_field(self):
        self.assertFormHasError({"main_field": "break_field"}, "invalid_field")
        self.assertFormHasError({"main_field": "break_field"}, "invalid_field", field_name="main_field")

        # Error is in main_field not fake_field
        self.raisesAssertionError(
            self.assertFormHasError, {"main_field": "break_field"}, "invalid_form", field_name="fake_field"
        )
        # This next data raises an error, just not the one with this code
        error = self.raisesAssertionError(
            self.assertFormHasError, {"main_field": "break_field"}, "invalid_data", field_name="main_field"
        )
        self.assertEqual(
            error.__str__(),
            "Form did not contain an error with code '{code}' in field '{field}'".format(
                code="invalid_data",
                field="main_field",
            ),
        )

    def test_assertFormHasError_in_form(self):
        self.assertFormHasError({"main_field": "break_form"}, "invalid_form")

        # Should raise no error
        error = self.raisesAssertionError(self.assertFormHasError, {"main_field": "break_nothing"}, "invalid_form")
        self.assertEqual(error.__str__(), "The form contained no errors")
        # Error is not in main_field, but elsewhere
        error = self.raisesAssertionError(
            self.assertFormHasError, {"main_field": "break_form"}, "invalid_form", field_name="main_field"
        )
        self.assertEqual(
            error.__str__(),
            "Form did not encounter an error in '{field_name}'.".format(
                field_name="main_field",
            ),
        )
        # Error code is not correct, but there is another error
        error = self.raisesAssertionError(self.assertFormHasError, {"main_field": "break_form"}, "invalid_field")
        self.assertEqual(
            error.__str__(),
            "Form did not contain an error with code '{code}'. Though there was another error: '{exception}'".format(
                code="invalid_field", exception="['Test form exception']"
            ),
        )
