from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, UpdateView

from membership_file.util import MembershipRequiredMixin
from user_interaction.accountcollective import AccountViewMixin

from membership_file.models import Member
from membership_file.forms import MemberForm


class MembershipDataView(AccountViewMixin, PermissionRequiredMixin, TemplateView):
    model = Member
    template_name = 'membership_file/membership_view.html'
    permission_required = 'membership_file.can_view_membership_information_self'


# Page for changing membership information using a form
class MembershipChangeView(MembershipRequiredMixin, AccountViewMixin, PermissionRequiredMixin, UpdateView):
    template_name = 'membership_file/membership_edit.html'
    form_class = MemberForm
    success_url = reverse_lazy('account:membership:view')
    permission_required = ('membership_file.can_view_membership_information_self', 'membership_file.can_change_membership_information_self')
    raise_exception = True

    def get_object(self, queryset=None):
        """
            Sets the view's object to the Member corresponding to the user that makes
            the request.
        """
        return self.request.member

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs['user'] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        # Members who are marked for deletion cannot edit their membership information
        obj = self.get_object()
        if obj is not None and obj.marked_for_deletion:
            return HttpResponseForbidden("Your membership is about to be cancelled. Please contact the board if this was a mistake.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        message = _("Your membership information has been saved successfully!")
        messages.success(self.request, message)
        return super().form_valid(form)
