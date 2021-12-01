from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, UpdateView

from core.views import AccountTabsMixin

from .forms import MemberForm
from .util import MembershipRequiredMixin

# Enable the auto-creation of logs
from .auto_model_update import *
from .export import *


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
