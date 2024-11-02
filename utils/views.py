from typing import Any, Dict, Optional, Type
from django.contrib.admin import helpers, ModelAdmin
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.forms import BaseModelForm
from django.http.response import HttpResponseRedirect
from django.contrib.messages import success, warning


from utils.forms import get_basic_filter_by_field_form


class PostOnlyFormViewMixin:
    form_success_method_name = "save"

    def get(self, request, *args, **kwargs):
        warning(request, "You can't visit the page you tried to... visit...")

        return HttpResponseRedirect(self.get_success_url())

    def form_valid(self, form):
        # Run the method
        getattr(form, self.form_success_method_name)()

        # Build the success message if provided
        success_message = self.get_success_message(form)
        if success_message:
            success(self.request, success_message)

        return super(PostOnlyFormViewMixin, self).form_valid(form)

    def form_invalid(self, form):
        # Build the faillure message if provided
        faillure_message = self.get_faillure_message(form)
        warning(self.request, faillure_message)

        return HttpResponseRedirect(self.get_success_url())

    def get_first_form_error(self, form):
        """Returns the error code from the first invalidation error found"""
        if form.errors:
            invalidation_errors = form.errors.as_data()
            first_error = invalidation_errors[list(invalidation_errors.keys())[0]][0]
            return first_error
        return None

    def get_success_message(self, form):
        return None

    def get_faillure_message(self, form):
        invalidation_error = self.get_first_form_error(form)
        return f"Action could not be performed; {invalidation_error.message}"


class RedirectMixin:
    """A mixin that takes 'redirect_to' from the GET parameters and applies that when necessary"""

    redirect_url_name = "redirect_to"

    def __init__(self, *args, **kwargs):
        self.redirect_to = None
        super(RedirectMixin, self).__init__(*args, **kwargs)

    def setup(self, request, *args, **kwargs):
        super(RedirectMixin, self).setup(request, *args, **kwargs)
        if self.redirect_url_name in request.GET.keys():
            self.redirect_to = self.request.GET.get(self.redirect_url_name)

    def get_context_data(self, *args, **kwargs):
        context = super(RedirectMixin, self).get_context_data(*args, **kwargs)
        context["redirect_to_url"] = self.redirect_to
        return context

    def get_success_url(self):
        if self.redirect_to:
            return self.redirect_to
        else:
            return super(RedirectMixin, self).get_success_url()


class SearchFormMixin:
    """A mixin for ListViews that allow filtering of the data in the queryset through a form"""

    search_form_class = None
    filter_field_name = None

    def get_filter_form(self):
        """Returns the initialised filter form"""
        if self.filter_field_name:
            form_class = get_basic_filter_by_field_form(self.filter_field_name)
        elif self.search_form_class:
            form_class = self.search_form_class
        else:
            raise KeyError(
                "Either 'search_form_class' or a 'filter_field_name' need to be defined" "to use SearchFormMixin"
            )
        return form_class(**self.get_filter_form_kwargs())

    def get_filter_form_kwargs(self, **kwargs):
        return {"data": self.request.GET, **kwargs}

    def dispatch(self, request, *args, **kwargs):
        self.search_form = self.get_filter_form()
        return super(SearchFormMixin, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(SearchFormMixin, self).get_queryset()
        return self.filter_data(queryset)

    def filter_data(self, queryset):
        if self.search_form.is_valid():
            return self.search_form.get_filtered_items(queryset)
        else:
            return queryset

    def get_context_data(self, **kwargs):
        return super(SearchFormMixin, self).get_context_data(filter_form=self.search_form, **kwargs)


class SuperUserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Verify that the current user is an admin"""

    def test_func(self):
        return self.request.user.is_superuser


class ModelAdminFormViewMixin:
    """
    A Mixin that allows a ModelForm (e.g in a CreateView) to be rendered
    inside a ModelAdmin in the admin panel using features normally available there.

    This includes default widgets and styling (e.g. for datetime) and formsets.

    The `form_class` must also inherit `utils.forms.FieldsetAdminFormMixin`
    in order for this to work.
    Furthermore, a `model_admin` should be passed in order to instantiate this view.
    """

    # Class variable needed as we need to be able to pass this through as_view(..)
    model_admin: ModelAdmin = None
    title = "Form title"
    subtitle = None
    breadcrumbs_title = None
    save_button_title = None
    template_name = "core/admin_form.html"

    def __init__(self, *args, model_admin: ModelAdmin = None, **kwargs) -> None:
        assert model_admin is not None
        self.model_admin = model_admin
        super().__init__(*args, **kwargs)

    def get_title(self):
        """Gets the title displayed at the top of the page"""
        return self.title

    def get_subtitle(self):
        """Gets the subtitle displayed at the top of the page"""
        return self.subtitle or self.object

    def get_breadcrumbs_title(self):
        """Gets the title used in the breadcrumbs. When None, uses `title`"""
        return self.breadcrumbs_title

    def get_save_button_title(self):
        """Gets the title used for the save button. Defaults to 'Save'"""
        return self.save_button_title

    def get_form(self, form_class: Optional[Type[BaseModelForm]] = None) -> BaseModelForm:
        # This method should return a form instance
        if form_class is None:
            form_class = self.get_form_class()

        # Use this form_class's excludes instead of those from the ModelAdmin's form_class
        exclude = None
        if hasattr(form_class, "_meta"):
            exclude = form_class._meta.exclude or ()

        # This constructs a form class
        # NB: More defaults can be passed into the **kwargs of ModelAdmin.get_form
        form_class = self.model_admin.get_form(
            self.request,
            None,
            change=False,
            # Fields are defined in the form
            fields=None,
            # Override standard ModelAdmin form and ignore its exclude list
            form=form_class,
            exclude=exclude,
        )

        # Use the newly constructed form class to create a form
        return super().get_form(form_class)

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        form = context.pop("form")
        adminForm = helpers.AdminForm(
            form, list(form.get_fieldsets(self.request, self.object)), {}, model_admin=self.model_admin
        )

        context.update(
            {
                **self.model_admin.admin_site.each_context(self.request),
                "title": self.get_title(),
                "subtitle": self.get_subtitle(),
                "adminform": adminForm,
                "original": self.object,
                "opts": self.model_admin.model._meta,
                "breadcrumbs_title": self.get_breadcrumbs_title(),
                "save_button_title": self.get_save_button_title(),
            }
        )

        return context
