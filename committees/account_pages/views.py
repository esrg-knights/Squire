from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView

from membership_file.util import MembershipRequiredMixin

from user_interaction.account_pages.mixins import AccountTabsMixin


class AssociationGroupAccountView(MembershipRequiredMixin, AccountTabsMixin, PermissionRequiredMixin, TemplateView):
    permission_required = ('membership_file.can_view_membership_information_self')
    template_name = "committees/account_group_overview.html"
    selected_tab_name = 'tab_association_groups'
