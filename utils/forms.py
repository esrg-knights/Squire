from django import forms
from django.core.exceptions import ObjectDoesNotExist


def get_basic_filter_by_field_form(field_name):
    """ Constructs a Form used for filtering querysets in a case insensitive manner """
    class FilterByFieldForm(forms.Form):
        search_field = forms.CharField(max_length=100, required=False, label=field_name)

        def get_filtered_items(self, queryset):
            return queryset.filter(name__icontains=self.cleaned_data['search_field']).order_by(field_name)

    return FilterByFieldForm


class FilterForm(forms.Form):
    """ Basic set-up for filtering through form """

    def get_filtered_items(self, queryset):
        raise NotImplementedError(
            "Any subclass of FilterForm should have a 'get_filtered_items(self, queryset)' method."
        )

class UpdatingUserFormMixin:
    """
        Form Mixin for ModelForms that, upon saving, updates a customizable
        field with a user passed at form initialisation. For example, by
        passing the requesting user to a FormView with this Mixin, this user
        represents the user that last updated the related model.
    """
    updating_user_field_name = 'last_updated_by'

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        # Sanity check (hasattr doesn't do the trick due to Foo.RelatedObjectDoesNotExist)
        try:
            getattr(self.instance, self.updating_user_field_name)
        except ObjectDoesNotExist:
            # This is fine; the field exists but there's just no object there yet
            pass
        except AttributeError:
            # This is not fine; the field does not exist for the instance!
            assert False, "%s has no field %s" % (self.instance.__class__, self.updating_user_field_name)

    def save(self, commit=True):
        # Update the field
        #   We only do this now as we don't want the current user to
        #   show up as the old value for this field
        setattr(self.instance, self.updating_user_field_name, self.user)
        return super().save(commit=commit)

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
