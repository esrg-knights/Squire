from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView

from committees.models import AssociationGroup


class AssocGroupOverview(PermissionRequiredMixin, ListView):
    permission_required = "committees.view_associationgroup"
    context_object_name = 'association_groups'
    group_type = None
    tab_name = None

    def get_queryset(self):
        return AssociationGroup.objects.filter(type=self.group_type, is_public=True)

    def get_context_data(self, *args, **kwargs):
        context = super(AssocGroupOverview, self).get_context_data(*args, **kwargs)
        context[self.tab_name] = True
        context['tabs'] = self.get_tab_data()
        return context

    def get_tab_data(self):
        tabs = [
            {'name': 'tab_committee', 'verbose': 'Committees', 'url_name': 'committees:committees'},
            {'name': 'tab_guild', 'verbose': 'Orders', 'url_name': 'committees:guilds'},
            {'name': 'tab_boards', 'verbose': 'Boards', 'url_name': 'committees:boards'},
        ]
        for tab in tabs:
            if tab['name'] == self.tab_name:
                tab['selected'] = True
        return tabs



class CommitteeOverview(AssocGroupOverview):
    template_name = "committees/overview_committees.html"
    group_type = AssociationGroup.COMMITTEE
    tab_name = 'tab_committee'


class GuildOverview(AssocGroupOverview):
    template_name = "committees/overview_guilds.html"
    group_type = AssociationGroup.ORDER
    tab_name = 'tab_guild'


class BoardOverview(AssocGroupOverview):
    template_name = "committees/overview_boards.html"
    group_type = AssociationGroup.BOARD
    tab_name = 'tab_boards'

    def get_queryset(self):
        # Reverse order to make sure latest boards are on top
        return super(BoardOverview, self).get_queryset().order_by('-shorthand')





