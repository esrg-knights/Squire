from functools import partial
from typing import Any, Dict, Optional, Type
from django.contrib import messages
from django.contrib.admin import helpers, ModelAdmin
from django.contrib.admin.utils import flatten_fieldsets
from django.core.exceptions import PermissionDenied
from django.forms.models import BaseModelForm
from django.http import HttpResponse
from django.views.generic.edit import CreateView
from django.views.generic import TemplateView, FormView
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy

from dynamic_preferences.registries import global_preferences_registry

from .util import MembershipRequiredMixin

# Enable the auto-creation of logs
from .auto_model_update import *
from .export import *
from membership_file.forms import ContinueMembershipForm, RegisterMemberForm
from membership_file.models import Membership

global_preferences = global_preferences_registry.manager()


class MemberMixin(MembershipRequiredMixin):
    """
    Sets the view's object to the Member corresponding to the user that makes
    the request.
    """

    def get_object(self, queryset=None):
        return self.request.member


# Page that loads whenever a user tries to access a member-page
class NotAMemberView(TemplateView):
    template_name = "membership_file/no_member.html"


class UpdateMemberYearMixin:
    year = None

    def setup(self, request, *args, **kwargs):
        self.year = global_preferences["membership__signup_year"]
        if self.year is None:
            raise PermissionDenied("There is no year active to extend")

        super(UpdateMemberYearMixin, self).setup(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UpdateMemberYearMixin, self).get_context_data(**kwargs)
        context["new_year"] = self.year
        return context


class ExtendMembershipView(MemberMixin, UpdateMemberYearMixin, FormView):
    template_name = "membership_file/extend_membership.html"
    form_class = ContinueMembershipForm
    success_url = reverse_lazy("membership_file/continue_success")

    def dispatch(self, request, *args, **kwargs):
        if Membership.objects.filter(year=self.year, member=self.request.member).exists():
            return TemplateResponse(
                request,
                template="membership_file/extend_membership_already_done.html",
                context=self.get_context_data(),
            )

        return super(ExtendMembershipView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(ExtendMembershipView, self).get_form_kwargs()
        kwargs.update({"member": self.request.member, "year": self.year})
        return kwargs

    def form_valid(self, form):
        form.save()
        msg = f"Succesfully extended Knights membership into {self.year}"
        messages.success(self.request, msg)
        return super(ExtendMembershipView, self).form_valid(form)


class ExtendMembershipSuccessView(MemberMixin, UpdateMemberYearMixin, TemplateView):
    template_name = "membership_file/extend_membership_successpage.html"


class ModelAdminFormViewMixin:
    """ TODO """
    model_admin: ModelAdmin = None

    def __init__(self, *args, model_admin: ModelAdmin=None, **kwargs) -> None:
        assert model_admin is not None
        self.model_admin = model_admin
        super().__init__(*args, **kwargs)

    def get_form(self, form_class: Optional[type[BaseModelForm]]=None) -> BaseModelForm:
        # This should return a form instance
        # NB: More defaults can be passed into the **kwargs of ModelAdmin.get_form
        if form_class is None:
            form_class = self.get_form_class()

        # Use this form_class's excludes instead of those from the ModelAdmin's form_class
        exclude = form_class._meta.exclude or ()

        # fields = flatten_fieldsets(self.get_fieldsets(request, obj))

        # print(form_class)

        # This constructs a form class
        form_class = self.model_admin.get_form(
            self.request, None, change=False,
            # Fields are defined in the form
            fields=None,
            # Override standard ModelAdmin form and ignore its exclude list
            form=form_class,
            exclude=exclude,
        )


        return super().get_form(form_class)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        form: RegisterMemberForm = context.pop("form")
        adminForm = helpers.AdminForm(form, list(form.get_fieldsets(self.request, self.object)), {}, model_admin=self.model_admin)
        # FORMFIELD_FOR_DBFIELD_DEFAULTS

        context.update(
            {
                "adminform": adminForm,
                # 'form_url': form_url,
                "is_nav_sidebar_enabled": True,
                "opts": Member._meta,
                "title": "Register new member",
                # 'content_type_id': get_content_type_for_model(self.model).pk,
                # 'app_label': app_label,
            }
        )

        return context


class RegisterNewMemberAdminView(ModelAdminFormViewMixin, CreateView):
    """placeholder"""

    form_class = RegisterMemberForm
    template_name = "membership_file/register_member.html"
    success_message = ""

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        self.email_sent = form.cleaned_data["send_registration_email"]
        return super().form_valid(form)

    def get_success_url(self) -> str:
        if self.email_sent:
            messages.success(self.request, f"Registered and emailed member “{self.object}”")
        else:
            messages.warning(self.request, f"Registered, but did not email member “{self.object}”")

        return reverse(f"admin:membership_file_member_change", args=(self.object.id,))

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)

        return context
