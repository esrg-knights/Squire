from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView

from user_interaction.accountcollective import AccountViewMixin


class AssociationGroupAccountView(AccountViewMixin, PermissionRequiredMixin, TemplateView):
    permission_required = "membership_file.can_view_membership_information_self"
    template_name = "committees/account_pages/account_group_overview.html"
