
from django.contrib import messages
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, TemplateView, UpdateView

from boardgames.models import BoardGame
from inventory.forms import FilterOwnershipThroughRelatedItems
from inventory.models import Ownership, Item, MiscellaneousItem
from inventory.views import OwnershipMixin
from roleplaying.models import RoleplayingItem
from utils.views import SearchFormMixin

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


class AssociationGroupDetailView(GroupMixin, TemplateView):
    template_name = "committees/group_detail_info.html"

    def get_context_data(self, **kwargs):
        context = super(AssociationGroupDetailView, self).get_context_data(**kwargs)
        context['tab_overview'] = True
        context['links_internal'] = self.construct_internal_links(self.group)
        context['links_external'] = self.group.associationgroup.shortcut_set.all()
        return context

    @staticmethod
    def construct_internal_links(group):
        links = []
        if group.permissions.filter(codename='maintain_ownerships_for_boardgame').exists():
            links.append({
                'url': reverse_lazy('inventory:catalogue', kwargs={'type_id': BoardGame}),
                'name': "Boardgame catalogue",
            })
        if group.permissions.filter(codename='maintain_ownerships_for_roleplayingitem').exists():
            links.append({
                'url': reverse_lazy('inventory:catalogue',  kwargs={'type_id': RoleplayingItem}),
                'name': "Roleplaying catalogue",
            })
        if group.permissions.filter(codename='maintain_ownerships_for_miscellaneousitem').exists():
            links.append({
                'url': reverse_lazy('inventory:catalogue',  kwargs={'type_id': MiscellaneousItem}),
                'name': "Misc item catalogue",
            })
        return links

class AssociationGroupInventoryView(GroupMixin, SearchFormMixin, ListView):
    template_name = "committees/group_detail_inventory.html"
    context_object_name = 'ownerships'
    search_form_class = FilterOwnershipThroughRelatedItems

    def get_queryset(self):
        ownerships = Ownership.objects.filter(group=self.group).filter(is_active=True)
        return self.filter_data(ownerships)

    def get_context_data(self, **kwargs):
        # Set a list of availlable content types
        # Used for url creation to add-item pages
        return super(AssociationGroupInventoryView, self).get_context_data(
            content_types=Item.get_item_contenttypes(),
            tab_inventory=True,
            **kwargs,
        )


class GroupItemLinkUpdateView(GroupMixin, OwnershipMixin, UpdateView):
    template_name = "committees/group_detail_inventory_link_update.html"
    model = Ownership
    fields = ['note', 'added_since']
    allow_access_through_group = True

    def get_object(self, queryset=None):
        return self.ownership

    def get_context_data(self, **kwargs):
        context = super(GroupItemLinkUpdateView, self).get_context_data(**kwargs)
        context['tab_inventory'] = True
        return context

    def form_valid(self, form):
        messages.success(self.request, f"Link data has been updated")
        return super(GroupItemLinkUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy("committees:group_inventory", kwargs={'group_id': self.group.id})
