from django import forms


def get_basic_filter_by_field_form(field_name):
    """ Constructs a Form used for filtering querysets in a case insensitive manner """
    class FilterByFieldForm(forms.Form):
        search_field = forms.CharField(max_length=100, required=False, label=field_name)

        def get_filtered_items(self, queryset):
            return queryset.filter(name__icontains=self.cleaned_data['search_field']).order_by(field_name)

    return FilterByFieldForm


class UserFormMixin:
    """
        Form Mixin that sets a variable to a user passed at form
        initialisation such that this user can be used in other methods.
        For example, this user can be the requesting user of a FormView
        that uses a form with this Mixin.
    """
    user = None

    def __init__(self, *args, user=None, **kwargs):
        self.user = user

        # We do not pass 'user' down the Form-chain, as other Forms
        #   may not know what to do with it
        super().__init__(*args, **kwargs)


class UpdatingUserFormMixin(UserFormMixin):
    """
        Form Mixin for ModelForms that, upon saving, updates a customizable
        field with a user passed at form initialisation. For example, by
        passing the requesting user to a FormView with this Mixin, this user
        represents the user that last updated the related model.
    """
    updating_user_field_name = 'last_updated_by'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Sanity check
        assert hasattr(self.instance, self.updating_user_field_name)

    def save(self, commit=True):
        # Update the field
        #   We only do this now as we don't want the current user to
        #   show up as the old value for this field
        setattr(self.instance, self.updating_user_field_name, self.user)
        return super().save(commit=commit)

class RequestUserToFormViewMixin:
    """
        Mixin that passes the requesting user as a kwarg to
        the View's Form.
    """
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class RequestUserToFormModelAdminMixin:
    """
        Mixin that passes the requeesting user as a kwarg to
        the ModelAdmin's Form.
    """
    def get_form(self, request, obj=None, **kwargs):
        Form = super().get_form(request, obj, **kwargs)

        # It'd be nice to use something like functools.partial(Form, user=request.user)
        #   but that doesn't expose class variables
        class RequestUserForm(Form):
            def __new__(cls, *args, **kwargs):
                return Form(*args, user=request.user, **kwargs)
        return RequestUserForm
