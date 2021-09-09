from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, TemplateView, UpdateView
from django.views.decorators.http import require_safe

from .forms import MemberForm
from .models import Member
from .util import MembershipRequiredMixin, membership_required

from core.views import TemplateManager

# Enable the auto-creation of logs
from .auto_model_update import *
from .export import *


# Add a link to each user's Account page leading to its Membership page
TemplateManager.set_template('core/user_accounts/account.html', 'membership_file/account_membership.html')


class MemberMixin(MembershipRequiredMixin):
    """
        Sets the view's object to the Member corresponding to the user that makes
        the request.
    """
    def get_object(self, queryset=None):
        return self.request.member


# Page that loads whenever a user tries to access a member-page
class NotAMemberView(TemplateView):
    template_name = 'membership_file/no_member.html'


# Page for viewing membership information
class MemberView(MemberMixin, PermissionRequiredMixin, DetailView):
    model = Member
    template_name = 'membership_file/view_member.html'
    permission_required = 'membership_file.can_view_membership_information_self'
    raise_exception = True

# Page for changing membership information using a form
class MemberChangeView(MemberMixin, PermissionRequiredMixin, UpdateView):
    template_name = 'membership_file/edit_member.html'
    form_class = MemberForm
    success_url = reverse_lazy('membership_file/membership')
    permission_required = ('membership_file.can_view_membership_information_self', 'membership_file.can_change_membership_information_self')
    raise_exception = True

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


# Renders the webpage for viewing a user's own membership information
@require_safe
@membership_required
@permission_required('membership_file.can_view_membership_information_self', raise_exception=True)
def viewGroups(request):
    return render(request, 'membership_file/member_group_overview.html', {})
