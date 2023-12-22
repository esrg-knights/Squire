import copy
from django import forms
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import ModelFormMetaclass


def get_basic_filter_by_field_form(field_name):
    """Constructs a Form used for filtering querysets in a case insensitive manner"""

    class FilterByFieldForm(forms.Form):
        search_field = forms.CharField(max_length=100, required=False, label=field_name)

        def get_filtered_items(self, queryset):
            return queryset.filter(name__icontains=self.cleaned_data["search_field"]).order_by(field_name)

    return FilterByFieldForm


class FilterForm(forms.Form):
    """Basic set-up for filtering through form"""

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

    updating_user_field_name = "last_updated_by"

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
    Mixin that passes the requesting user as a kwarg to
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


class FormGroup:
    """
    A formgroup functions as a shell to a form and any number of formsets. This is ideal when editing an
    object along with some directly related objects. Can be used on FormViews
    form_class: The class of the main form
    formset_class: The class of the formset
    form_kwargs: dictionary of form init arguments
    formset_kwargs: dictionary of dictionaries with formset init keyword arguments. Keys are names of the formset classes
    i.e. {'MyFormset': {'Init_keyword': 'value'}}
    """

    form_class = None
    form_kwargs = {}
    formset_kwargs = {}
    formset_class = None

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.form = self.form_class(**self.get_form_kwargs(self.form_class))
        self.formsets = [self.formset_class(**self.get_formset_kwargs(self.formset_class))]

    def get_form_kwargs(self, form_class):
        """Get the form initial keyword arguments for the form"""
        kwargs = {}
        # Carry over the basic init kwargs over to the form, but no more as any unexpected kwarg throws an exception
        # in the form itself
        _form_base_init_kwargs = ["data", "files", "auto_id", "error_class", "label_suffix", "renderer"]
        for kwarg_key in _form_base_init_kwargs:
            if kwarg_key in self.init_kwargs:
                kwargs[kwarg_key] = self.init_kwargs[kwarg_key]

        if self.init_kwargs.get("prefix", None):
            kwargs["prefix"] = self.init_kwargs["prefix"] + "-"
        kwargs["prefix"] = kwargs.get("prefix", "") + "main"
        kwargs.update(self.form_kwargs)
        return kwargs

    def get_formset_kwargs(self, formset_class):
        """Get the form initial keyword arguments for the formset"""
        kwargs = {}
        # Carry over the basic init kwargs over to the formset, but no more as any unexpected kwarg throws an exception
        # in the formset itself
        _formset_base_init_kwargs = ["data", "files", "auto_id", "error_class"]
        for kwarg_key in _formset_base_init_kwargs:
            if kwarg_key in self.init_kwargs:
                kwargs[kwarg_key] = self.init_kwargs[kwarg_key]

        if self.init_kwargs.get("prefix", None):
            kwargs["prefix"] = self.init_kwargs["prefix"] + "-"
        kwargs["prefix"] = kwargs.get("prefix", "") + "formset"

        kwargs.update(self.formset_kwargs.get(formset_class.__name__, {}))
        return kwargs

    def is_valid(self):
        """Checks if any and all subforms and formsets are valid"""
        is_valid = True

        # Run over all forms and formsets to ensure that errors are build
        if not self.form.is_valid():
            is_valid = False
        for formset in self.formsets:
            if not formset.is_valid():
                is_valid = False

        return is_valid

    def save(self):
        """Executes save() on all forms and formsets (if applicable)"""
        if hasattr(self.form, "save"):
            self.form.save()
        for formset in self.formsets:
            if hasattr(formset, "save"):
                formset.save()


class FieldsetModelFormMetaclass(ModelFormMetaclass):
    """Sets the `_meta.fieldsets` attribute that is required by the admin panel."""

    def __new__(mcs, name, bases, attrs):
        new_class = super().__new__(mcs, name, bases, attrs)
        new_class._meta.fieldsets = None
        meta_class = getattr(new_class, "Meta", None)
        if meta_class is not None:
            new_class._meta.fieldsets = getattr(meta_class, "fieldsets", None)
        return new_class


class FieldsetAdminFormMixin(metaclass=FieldsetModelFormMetaclass):
    """
    This mixin allows a form to be used in the admin panel. Notably allows using fieldsets
    and default admin widgets (e.g. the datetime picker)
    """

    required_css_class = "required"

    # ModelAdmin media
    @property
    def media(self):
        extra = "" if settings.DEBUG else ".min"
        js = [
            "vendor/jquery/jquery%s.js" % extra,
            "jquery.init.js",
            "core.js",
            "admin/RelatedObjectLookups.js",
            "actions.js",
            "urlify.js",
            "prepopulate.js",
            "vendor/xregexp/xregexp%s.js" % extra,
        ]
        return forms.Media(js=["admin/js/%s" % url for url in js]) + super().media

    def get_fieldsets(self, request, obj=None):
        """
        Hook for specifying fieldsets.
        """
        if self._meta.fieldsets:
            return copy.deepcopy(self._meta.fieldsets)
        return [(None, {"fields": self.fields})]
