from django.forms import Form


class FormValidityMixin:
    """A mixin for TestCase classes designed to add form functionality"""

    form_class = None

    def get_form_kwargs(self, **kwargs):
        return kwargs

    def build_form(self, data, form_class=None, **kwargs) -> Form:
        """Builds the form, form_class can overwrite the default class attribute form_class"""
        if form_class is None:
            form_class = self.form_class
        return form_class(data=data, **self.get_form_kwargs(**kwargs))

    def assertHasField(self, field_name, form_kwargs=None, **field_properties):
        """
        Asserts that the form has a field with the given name
        :param form_kwargs: Keyword arguments for the form creation
        :param field_name: name of the field
        :param field_properties: Keywords that check parameters of the field. Use '__class' to check class type instead
        :return: raises AssertionError if not asserted, otherwise returns empty
        """
        form_kwargs = form_kwargs or {}
        form = self.build_form({}, **form_kwargs)
        fail_message = f"{field_name} was not a field in {form.__class__.__name__}"
        self.assertIn(field_name, form.fields, msg=fail_message)

        field = form.fields[field_name]
        for key, value in field_properties.items():
            try:
                if key.endswith("__class"):
                    key = key[: -len("__class")]
                    field_property = getattr(field, key)
                    fail_message = (
                        "{field_name}.{key} was not of type '{expected_type}', but '{actual_type}' instead".format(
                            field_name=field_name,
                            key=key,
                            expected_type=value.__name__,
                            actual_type=field_property.__class__.__name__,
                        )
                    )
                    self.assertIsInstance(field_property, value, msg=fail_message)
                else:
                    field_property = getattr(field, key)
                    fail_message = (
                        "{field_name}.{key} was not '{expected_value}', but '{actual_value}' instead".format(
                            field_name=field_name, key=key, expected_value=value, actual_value=field_property
                        )
                    )
                    self.assertEqual(field_property, value, msg=fail_message)
            except AttributeError:
                fail_message = f"Field name {field_name} did not contain the property {key}"
                raise AssertionError(fail_message)

    def assertFormValid(self, data, form_class=None, **form_kwargs):
        """Asserts that the form is valid otherwise raises AssertionError mentioning the form error
        :param data: The form data
        :param form_class: The form class, defaults to self.form_class
        :param form_kwargs: Any form init kwargs not defined in self.build_form()
        :return: returns the created valid form
        """
        form = self.build_form(data, form_class=form_class, **form_kwargs)

        if not form.is_valid():
            fail_message = "The form was not valid. At least one error was encountered: "

            invalidation_errors = form.errors.as_data()
            error_key = list(invalidation_errors.keys())[0]
            invalidation_error = invalidation_errors[error_key][0]
            fail_message += f"'{invalidation_error.message}' in '{error_key}'"
            raise AssertionError(fail_message)
        return form

    def assertFormNotHasError(self, data, code, form_class=None, field_name=None, **form_kwargs):
        """Opposite of assertFormHasError"""
        try:
            error = self.assertFormHasError(data, code, form_class=form_class, field_name=field_name, **form_kwargs)
        except AssertionError:
            return
        raise AssertionError("Unexpectedly encountered an error", error)

    def assertFormHasError(self, data, code, form_class=None, field_name=None, **form_kwargs):
        """Asserts that a form with the given data invalidates on a certain error
        :param data: The form data
        :param code: the 'code' of the ValidationError
        :param form_class: The form class, defaults to self.form_class
        :param field_name: The field on which the validationerror needs to be, set to '__all__' if it's not form specefic
        leave empty if not relevant.
        :param form_kwargs: Any form init kwargs not defined in self.build_form()
        :return:
        """
        form = self.build_form(data, form_class=form_class, **form_kwargs)

        if form.is_valid():
            raise AssertionError("The form contained no errors")

        for key, value in form.errors.as_data().items():
            if field_name:
                if field_name != key:
                    continue
                for error in value:
                    if error.code == code:
                        return error
                raise AssertionError(f"Form did not contain an error with code '{code}' in field '{field_name}'")
            else:
                for error in value:
                    if error.code == code:
                        return error

        if field_name:
            raise AssertionError(f"Form did not encounter an error in '{field_name}'.")

        error_message = f"Form did not contain an error with code '{code}'."
        if form.errors:
            invalidation_errors = form.errors.as_data()
            invalidation_error = invalidation_errors[list(invalidation_errors.keys())[0]][0]
            error_message += f" Though there was another error: '{invalidation_error}'"
        raise AssertionError(error_message)
