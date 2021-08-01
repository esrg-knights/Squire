

class FormValidityMixin:
    """ A mixin for TestCase classes designed to add form functionality """
    form_class = None

    def get_form_kwargs(self, **kwargs):
        return kwargs

    def build_form(self, data, form_class=None, **kwargs):
        """ Builds the form, form_class can overwrite the default class attribute form_class """
        if form_class is None:
            form_class = self.form_class
        return form_class(data=data, **self.get_form_kwargs(**kwargs))

    def assertHasField(self, field_name):
        """
        Asserts that the form has a field with the given name
        :param field_name: name of the field
        :return: raises AssertionError if not asserted, otherwise returns empty
        """
        form = self.build_form({})
        message = f"{field_name} was not a field in {form.__class__.__name__}"
        self.assertIn(field_name, form.fields, msg=message)

    def assertFormValid(self, data, form_class=None, **kwargs):
        """ Asserts that the form is valid otherwise raises AssertionError mentioning the form error
        :param data: The form data
        :param form_class: The form class, defaults to self.form_class
        :param kwargs: Any form init kwargs not defined in self.build_form()
        :return:
        """
        form = self.build_form(data, form_class=form_class, **kwargs)

        if not form.is_valid():
            fail_message = "The form was not valid. At least one error was encountered: "

            invalidation_errors = form.errors.as_data()
            error_key = list(invalidation_errors.keys())[0]
            invalidation_error = invalidation_errors[error_key][0]
            fail_message += f"'{invalidation_error.message}' in '{error_key}'"
            raise AssertionError(fail_message)
        return form

    def assertFormHasError(self, data, code, form_class=None, field=None, **kwargs):
        """ Asserts that a form with the given data invalidates on a certain error
        :param data: The form data
        :param code: the 'code' of the ValidationError
        :param form_class: The form class, defaults to self.form_class
        :param field: The field on which the validationerror needs to be, set to '__all__' if it's not form specefic
        leave empty if not relevant.
        :param kwargs: Any form init kwargs not defined in self.build_form()
        :return:
        """
        form = self.build_form(data, form_class=form_class, **kwargs)

        if form.is_valid():
            raise AssertionError("The form contained no errors")

        for key, value in form.errors.as_data().items():
            if field:
                if field != key:
                    continue
                for error in value:
                    if error.code == code:
                        return
                raise AssertionError(f"Form did not contain an error with code '{code}' in field '{field}'")
            else:
                for error in value:
                    if error.code == code:
                        return

        if field:
            raise AssertionError(f"Form did not encounter an error in '{field}'.")

        error_message = f"Form did not contain an error with code '{code}'."
        if form.errors:
            invalidation_errors = form.errors.as_data()
            invalidation_error = invalidation_errors[list(invalidation_errors.keys())[0]][0]
            error_message += f" Though there was another error: '{invalidation_error}'"
        raise AssertionError(error_message)
