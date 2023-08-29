from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.views.generic import TemplateView, FormView
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from dynamic_preferences.registries import global_preferences_registry

from .util import MembershipRequiredMixin

# Enable the auto-creation of logs
from .auto_model_update import *
from .export import *
from membership_file.forms import ContinueMembershipForm
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
