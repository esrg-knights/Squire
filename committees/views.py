
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.views.generic import ListView

from committees.models import AssociationGroup


class AssocGroupOverview(ListView):
    template_name = "committees/overview.html"
    context_object_name = 'association_groups'
    group_type = None
    tab_name = None

    def get_queryset(self):
        return AssociationGroup.objects.filter(type=self.group_type, is_public=True)

    def get_context_data(self, *args, **kwargs):
        context = super(AssocGroupOverview, self).get_context_data(*args, **kwargs)
        context[self.tab_name] = True
        return context


class CommitteeOverview(AssocGroupOverview):
    template_name = "committees/committees.html"
    group_type = AssociationGroup.COMMITTEE
    tab_name = 'tab_committee'


class GuildOverview(AssocGroupOverview):
    template_name = "committees/guilds.html"
    group_type = AssociationGroup.GUILD
    tab_name = 'tab_guild'


class BoardOverview(AssocGroupOverview):
    template_name = "committees/boards.html"
    group_type = AssociationGroup.BOARD
    tab_name = 'tab_boards'


class GroupMixin:
    """ Mixin that stores the retrieved group from the url group_id keyword. Also verifies user is part of that group """
    group = None

    def dispatch(self, request, *args, **kwargs):
        self.group = get_object_or_404(Group, id=self.kwargs['group_id'])
        if self.group not in self.request.user.groups.all():
            raise PermissionDenied()

        return super(GroupMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(GroupMixin, self).get_context_data(**kwargs)
        context['group'] = self.group
        return context
