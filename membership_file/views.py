from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_safe
from django.views.generic import DetailView, TemplateView, UpdateView
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from .models import Member, MemberLog, MemberUser, 
from .forms import MemberForm
from .util import MembershipRequiredMixin

from core.views import TemplateManager

# Enable the auto-creation of logs
from .auto_model_update import *
from .export import *


# Add a link to each user's Account page leading to its Membership page
TemplateManager.set_template('core/user_accounts/account.html', 'membership_file/account_membership.html')

# Makes the requesting user a MemberUser, and sets it as the relevant object
class RequestMemberMixin():
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        # Odd loop-around because all logged in users should be treated as memberusers
        if self.request.user.is_authenticated:
            self.request.user.__class__ = MemberUser
    
    def get_object(self, queryset=None):
        return None if not self.request.user.is_authenticated else self.request.user.get_member()


# Page that loads whenever a user tries to access a member-page
class NotAMemberView(TemplateView):
    template_name = 'membership_file/no_member.html'


# Page for viewing membership information
class MemberView(LoginRequiredMixin, RequestMemberMixin, MembershipRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Member
    template_name = 'membership_file/view_member.html'
    permission_required = 'membership_file.can_view_membership_information_self'
    raise_exception = True

# Page for changing membership information using a form
class MemberChangeView(LoginRequiredMixin, RequestMemberMixin, MembershipRequiredMixin, PermissionRequiredMixin, UpdateView):
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
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        message = _("Your membership information has been saved successfully!")
        messages.success(self.request, message)
        return super().form_valid(form)