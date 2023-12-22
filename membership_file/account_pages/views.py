from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, UpdateView
from dynamic_preferences.registries import global_preferences_registry

from membership_file.util import MembershipRequiredMixin
from user_interaction.accountcollective import AccountViewMixin

from membership_file.models import Member, Membership
from membership_file.forms import MemberForm


global_preferences = global_preferences_registry.manager()


class MembershipDataView(AccountViewMixin, PermissionRequiredMixin, TemplateView):
    model = Member
    template_name = "membership_file/membership_view.html"
    permission_required = "membership_file.can_view_membership_information_self"

    def get_context_data(self, **kwargs):
        context = super(MembershipDataView, self).get_context_data(**kwargs)
        year = global_preferences["membership__signup_year"]
        if year is not None and not Membership.objects.filter(member=self.request.member, year=year).exists():
            context["sign_up_message"] = {
                "msg_text": f"A new adventure awaits! Continue your membership into {year} now!",
                "msg_type": "info",
                "btn_text": "Continue Questing!",
                "btn_url": reverse_lazy("membership:continue_membership"),
            }
        context["memberyears"] = self.request.member.memberyear_set.order_by("name")
        # Due to overlapping years at the beginning of the year we need to take multiple instances into account
        context["activeyears"] = Membership.objects.filter(member=self.request.member, year__is_active=True)
        return context


# Page for changing membership information using a form
class MembershipChangeView(MembershipRequiredMixin, AccountViewMixin, PermissionRequiredMixin, UpdateView):
    template_name = "membership_file/membership_edit.html"
    form_class = MemberForm
    success_url = reverse_lazy("account:membership:view")
    permission_required = (
        "membership_file.can_view_membership_information_self",
        "membership_file.can_change_membership_information_self",
    )
    raise_exception = True
    requires_active_membership = False

    def get_object(self, queryset=None):
        """
        Sets the view's object to the Member corresponding to the user that makes
        the request.
        """
        return self.request.member

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs["user"] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        # Members who are marked for deletion cannot edit their membership information
        obj = self.get_object()
        if obj is not None and obj.marked_for_deletion:
            return HttpResponseForbidden(
                "Your membership is about to be cancelled. Please contact the board if this was a mistake."
            )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        message = _("Your membership information has been saved successfully!")
        messages.success(self.request, message)
        return super().form_valid(form)
