from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.views.generic import ListView, UpdateView

from inventory.forms import FilterOwnershipThroughRelatedItems
from inventory.models import Ownership, Item
from inventory.views import OwnershipMixin
from utils.views import SearchFormMixin


from committees.views import AssociationGroupMixin


class AssociationGroupInventoryView(AssociationGroupMixin, SearchFormMixin, ListView):
    template_name = "inventory/committee_pages/group_detail_inventory.html"
    context_object_name = 'ownerships'
    search_form_class = FilterOwnershipThroughRelatedItems

    def get_queryset(self):
        ownerships = Ownership.objects.filter(group=self.association_group.site_group).filter(is_active=True)
        return self.filter_data(ownerships)

    def get_context_data(self, **kwargs):
        # Set a list of availlable content types
        # Used for url creation to add-item pages
        adjustable_items = []
        for item in Item.get_item_contenttypes():
            perm_name = f'{item.app_label}.add_group_ownership_for_{item.model}'
            if self.request.user.has_perm(perm_name):
                adjustable_items.append(item)

        return super(AssociationGroupInventoryView, self).get_context_data(
            content_types=adjustable_items,
            tab_selected='tab_inventory',
            **kwargs,
        )


class AssociationGroupItemLinkUpdateView(AssociationGroupMixin, OwnershipMixin, UpdateView):
    template_name = "inventory/committee_pages/group_detail_inventory_link_update.html"
    model = Ownership
    fields = ['note', 'added_since']
    allow_access_through_group = True

    def get_object(self, queryset=None):
        return self.ownership

    def get_context_data(self, **kwargs):
        context = super(AssociationGroupItemLinkUpdateView, self).get_context_data(**kwargs)
        context['tab_selected'] = 'tab_inventory'
        return context

    def form_valid(self, form):
        messages.success(self.request, f"Link data has been updated")
        return super(AssociationGroupItemLinkUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy("committees:group_inventory", kwargs={'group_id': self.association_group.id})
