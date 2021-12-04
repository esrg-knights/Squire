from django.views.generic import TemplateView

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
