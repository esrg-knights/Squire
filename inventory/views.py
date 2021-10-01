from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http.response import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView
from django.views.generic.edit import FormView, UpdateView, CreateView

from committees.utils import user_in_association_group
from membership_file.util import MembershipRequiredMixin
from utils.views import SearchFormMixin, RedirectMixin

from inventory.models import Ownership, Item
from inventory.forms import *


__all__ = ['MemberItemsOverview', 'MemberItemRemovalFormView', 'MemberItemLoanFormView',
           'MemberOwnershipAlterView', 'OwnershipMixin', 'TypeCatalogue',
           'AddLinkCommitteeView', 'AddLinkMemberView', 'CreateItemView', 'UpdateItemView', 'DeleteItemView',
           'ItemLinkMaintenanceView', 'UpdateCatalogueLinkView', 'LinkActivationStateView', 'LinkDeletionView',]


class MemberItemsOverview(MembershipRequiredMixin, ListView):
    template_name = "inventory/membership_inventory.html"
    context_object_name = 'ownerships'

    def get_queryset(self):
        return Ownership.objects.filter(member=self.request.member).filter(is_active=True)

    def get_context_data(self, *args, **kwargs):
        context = super(MemberItemsOverview, self).get_context_data(*args, **kwargs)
        # Get items previously stored at the associatoin
        context[self.context_object_name+'_history'] = Ownership.objects.\
            filter(member=self.request.member).\
            filter(is_active=False)
        return context


class OwnershipMixin:
    """ A mixin for views that deal with Ownership items through the url ownership_id keyword """
    ownership = None
    allow_access_through_group = False

    def dispatch(self, request, *args, **kwargs):
        self.ownership = get_object_or_404(Ownership, id=self.kwargs['ownership_id'])
        self.check_access()
        return super(OwnershipMixin, self).dispatch(request, *args, **kwargs)

    def check_access(self):
        if self.ownership.member:
            if self.request.member == self.ownership.member:
                return
        elif self.allow_access_through_group:
            if self.ownership.group and user_in_association_group(
                self.request.user,
                self.ownership.group.associationgroup
            ):
                return
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super(OwnershipMixin, self).get_context_data(**kwargs)
        context['ownership'] = self.ownership
        return context


class MemberItemRemovalFormView(MembershipRequiredMixin, OwnershipMixin, FormView):
    template_name = "inventory/membership_take_home.html"
    form_class = OwnershipRemovalForm
    success_url = reverse_lazy("inventory:member_items")

    def get_form_kwargs(self):
        kwargs = super(MemberItemRemovalFormView, self).get_form_kwargs()
        kwargs['ownership'] = self.ownership
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f"{self.ownership.content_object} has been marked as taken home")
        return super(MemberItemRemovalFormView, self).form_valid(form)

    def form_invalid(self, form):
        message = f"This action was not possible: {form.non_field_errors()[0]}"
        messages.error(self.request, message)
        # Form is fieldless, invalid thus means user can't address it
        return HttpResponseRedirect(self.get_success_url())


class MemberItemLoanFormView(MembershipRequiredMixin, OwnershipMixin, FormView):
    template_name = "inventory/membership_loan_out.html"
    form_class = OwnershipActivationForm
    success_url = reverse_lazy("inventory:member_items")

    def get_form_kwargs(self):
        kwargs = super(MemberItemLoanFormView, self).get_form_kwargs()
        kwargs['ownership'] = self.ownership
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f"{self.ownership.content_object} has been marked as stored at the Knights")
        return super(MemberItemLoanFormView, self).form_valid(form)

    def form_invalid(self, form):
        message = f"This action was not possible: {form.non_field_errors()[0]}"
        messages.error(self.request, message)
        # Form is fieldless, invalid thus means user can't address it
        return HttpResponseRedirect(self.get_success_url())


class MemberOwnershipAlterView(MembershipRequiredMixin, OwnershipMixin, FormView):
    template_name = "inventory/membership_adjust_note.html"
    form_class = OwnershipNoteForm
    success_url = reverse_lazy("inventory:member_items")

    def get_form_kwargs(self):
        kwargs = super(MemberOwnershipAlterView, self).get_form_kwargs()
        kwargs['instance'] = self.ownership
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f"Your version of {self.ownership.content_object} has been updated")
        return super(MemberOwnershipAlterView, self).form_valid(form)


###########################################################
###############        Catalogue        ###################
###########################################################


class CatalogueMixin:
    """ Mixin that stores the retrieved item type from the url type_id keyword """
    item_type = None    # Item item for this catalogue

    def setup(self, request, *args, **kwargs):
        super(CatalogueMixin, self).setup(request, *args, **kwargs)
        self.item_type = kwargs.get('type_id')

    def get_context_data(self, *args, **kwargs):
        context = super(CatalogueMixin, self).get_context_data(*args, **kwargs)
        context.update({
            'item_type': self.item_type,
        })
        return context


class ItemMixin:
    """ Mixin that stores the retrieved item from the url type_id keyword. Requires CatalogueMixin or self.item_type """
    item = None

    def dispatch(self, request, *args, **kwargs):
        try:
            self.item = self.item_type.get_object_for_this_type(id=self.kwargs['item_id'])
        except self.item_type.model_class().DoesNotExist:
            raise Http404

        return super(ItemMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(ItemMixin, self).get_context_data(*args, **kwargs)
        context.update({
            'item': self.item,
        })
        return context


class TypeCatalogue(MembershipRequiredMixin, CatalogueMixin, SearchFormMixin, ListView):
    template_name = "inventory/catalogue_for_type.html"
    search_form_class = FilterCatalogueForm

    paginate_by = 15

    @property
    def model(self):
        # model as attribute is called by the list queryset
        # This patch is needed to let listview catalogue and searchform work
        return self.item_type.model_class()

    def get_filter_form_kwargs(self, **kwargs):
        item_class_name = self.item_type.model
        item_app_label = self.item_type.app_label

        return super(TypeCatalogue, self).get_filter_form_kwargs(
            item_type=self.item_type,
            include_owner=self.request.user.has_perm(f'{item_app_label}.maintain_ownerships_for_{item_class_name}')
        )

    def get_context_data(self, *args, **kwargs):
        context = super(TypeCatalogue, self).get_context_data(*args, **kwargs)

        item_class_name = self.item_type.model
        item_app_label = self.item_type.app_label
        context.update({
            'can_add_to_group': self.request.user.has_perm(f'{item_app_label}.add_group_ownership_for_{item_class_name}'),
            'can_add_to_member': self.request.user.has_perm(f'{item_app_label}.add_member_ownership_for_{item_class_name}'),
            'can_add_items': self.request.user.has_perm(f'{item_app_label}.add_{item_class_name}'),
            'can_change_items': self.request.user.has_perm(f'{item_app_label}.change_{item_class_name}'),
            'can_maintain_ownerships': self.request.user.has_perm(f'{item_app_label}.maintain_ownerships_for_{item_class_name}'),
        })
        return context


class AddLinkFormMixin:
    """ Mixin for the two AddLink Views that initialise common properties """
    template_name = "inventory/catalogue_add_link.html"

    def get_form_kwargs(self):
        kwargs = super(AddLinkFormMixin, self).get_form_kwargs()
        kwargs['item'] = self.item
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f"{self.item} has been placed in {form.instance.owner}'s inventory")
        return super(AddLinkFormMixin, self).form_valid(form)


class AddLinkCommitteeView(MembershipRequiredMixin, CatalogueMixin, ItemMixin, AddLinkFormMixin,
                           RedirectMixin, PermissionRequiredMixin, CreateView):
    form_class = AddOwnershipCommitteeLinkForm

    def get_form_kwargs(self):
        kwargs = super(AddLinkCommitteeView, self).get_form_kwargs()
        item_class_name = self.item_type.model
        item_app_label = self.item_type.app_label
        kwargs['allow_all_groups'] = self.request.user.has_perm(f'{item_app_label}.maintain_ownerships_for_{item_class_name}')
        return kwargs

    def get_permission_required(self):
        item_class_name = self.item_type.model
        item_app_label = self.item_type.app_label
        return [f'{item_app_label}.add_group_ownership_for_{item_class_name}']

    def get_success_url(self):
        if self.redirect_to:
            return self.redirect_to
        # Go back to the committee page
        return reverse_lazy("inventory:catalogue", kwargs={'type_id': self.item_type})


class AddLinkMemberView(MembershipRequiredMixin, CatalogueMixin, ItemMixin, AddLinkFormMixin,
                        RedirectMixin, PermissionRequiredMixin, FormView):
    form_class = AddOwnershipMemberLinkForm

    def get_permission_required(self):
        item_class_name = self.item_type.model
        item_app_label = self.item_type.app_label
        return [f'{item_app_label}.add_member_ownership_for_{item_class_name}']

    def get_success_url(self):
        if self.redirect_to:
            return self.redirect_to
        # Go back to the catalogue page
        return reverse_lazy("inventory:catalogue", kwargs={'type_id': self.item_type})


class CreateItemView(MembershipRequiredMixin, CatalogueMixin, PermissionRequiredMixin, CreateView):
    template_name = "inventory/catalogue_add_item.html"
    fields = '__all__'

    @property
    def model(self):
        return self.item_type.model_class()

    def get_permission_required(self):
        item_class_name = self.item_type.model
        item_app_label = self.item_type.app_label
        return [f'{item_app_label}.add_{item_class_name}']

    def form_valid(self, form):
        msg = "{item_name} has been created".format(item_name=form.instance.name)
        messages.success(self.request, msg)
        self.instance = form.instance
        return super(CreateItemView, self).form_valid(form)

    def get_success_url(self):
        if 'btn_save_to_member' in self.request.POST.keys():
            return reverse('inventory:catalogue_add_member_link', kwargs={
                'type_id': self.item_type,
                'item_id': self.instance.id,
            })
        elif 'btn_save_to_group' in self.request.POST.keys():
            return reverse('inventory:catalogue_add_group_link', kwargs={
                'type_id': self.item_type,
                'item_id': self.instance.id,
            })
        return reverse('inventory:catalogue', kwargs={'type_id': self.item_type})


class UpdateItemView(RedirectMixin, MembershipRequiredMixin, CatalogueMixin, ItemMixin, PermissionRequiredMixin, UpdateView):
    template_name = "inventory/catalogue_change_item.html"
    fields = '__all__'

    @property
    def model(self):
        return self.item_type.model_class()

    def get_object(self, queryset=None):
        return self.item

    def get_permission_required(self):
        item_class_name = self.item_type.model
        item_app_label = self.item_type.app_label
        return [f'{item_app_label}.change_{item_class_name}']

    def form_valid(self, form):
        msg = "{item_name} has been updated".format(item_name=form.instance.name)
        messages.success(self.request, msg)
        return super(UpdateItemView, self).form_valid(form)

    def get_success_url(self):
        if self.redirect_to:
            return self.redirect_to

        if 'btn_save_to_member' in self.request.POST.keys():
            return reverse('inventory:catalogue_add_member_link', kwargs={
                'type_id': self.item_type,
                'item_id': self.item.id,
            })
        elif 'btn_save_to_group' in self.request.POST.keys():
            return reverse('inventory:catalogue_add_group_link', kwargs={
                'type_id': self.item_type,
                'item_id': self.item.id,
            })

        return reverse('inventory:catalogue', kwargs={'type_id': self.item_type})


class DeleteItemView(MembershipRequiredMixin, CatalogueMixin, ItemMixin, RedirectMixin, PermissionRequiredMixin, FormView):
    template_name = "inventory/catalogue_delete_item.html"
    form_class = DeleteItemForm

    def get_form_kwargs(self):
        # Check user delete_links_permission
        item_class_name = self.item_type.model
        item_app_label = self.item_type.app_label
        permission_name = f'{item_app_label}.maintain_ownerships_for_{item_class_name}'
        ignore_active_links = self.request.user.has_perm(permission_name)

        kwargs = super(DeleteItemView, self).get_form_kwargs()
        kwargs.update({
            'item': self.item,
            'ignore_active_links': ignore_active_links,
        })
        return kwargs

    def get_context_data(self, *args, **kwargs):
        item_class_name = self.item_type.model
        item_app_label = self.item_type.app_label
        permission_name = f'{item_app_label}.maintain_ownerships_for_{item_class_name}'

        return super(DeleteItemView, self).get_context_data(
            active_links=self.item.currently_in_possession(),
            can_maintain_ownerships=self.request.user.has_perm(permission_name),
            **kwargs
        )

    def get_permission_required(self):
        item_class_name = self.item_type.model
        item_app_label = self.item_type.app_label
        return [f'{item_app_label}.delete_{item_class_name}']

    def form_valid(self, form):
        msg = "{item_name} has been deleted".format(item_name=self.item.name)
        messages.success(self.request, msg)
        form.delete_item()
        return super(DeleteItemView, self).form_valid(form)

    def get_success_url(self):
        return reverse('inventory:catalogue', kwargs={'type_id': self.item_type})


###############  Catalogue link editing  ###################


class ItemLinkMaintenanceView(MembershipRequiredMixin, CatalogueMixin, ItemMixin, PermissionRequiredMixin, DetailView):
    template_name = "inventory/catalogue_item_info_view.html"

    def get_object(self, queryset=None):
        return self.item

    def get_permission_required(self):
        item_class_name = self.item_type.model
        item_app_label = self.item_type.app_label
        return [f'{item_app_label}.maintain_ownerships_for_{item_class_name}']

    def get_context_data(self, *args, **kwargs):
        item_class_name = self.item_type.model
        item_app_label = self.item_type.app_label
        context = super(ItemLinkMaintenanceView, self).get_context_data(*args, **kwargs)
        context.update({
            'active_links': self.item.currently_in_possession(),
            'inactive_links': self.item.ownerships.filter(is_active=False),
            'can_add_to_group': self.request.user.has_perm(f'{item_app_label}.add_group_ownership_for_{item_class_name}'),
            'can_add_to_member': self.request.user.has_perm(f'{item_app_label}.add_member_ownership_for_{item_class_name}'),
            'can_delete': self.request.user.has_perm(f'{item_app_label}.delete_{item_class_name}'),
        })
        return context


class OwnershipCatalogueLinkMixin:
    """ Mixin that retrieves ownership links for a context suitable for catalogue maintenance """
    def dispatch(self, request, *args, **kwargs):
        self.ownership = get_object_or_404(Ownership, id=kwargs.get('link_id', None))
        # Assure that the ownership and item are linked correctly
        if self.ownership.content_object != self.item:
            raise Http404()

        return super(OwnershipCatalogueLinkMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(OwnershipCatalogueLinkMixin, self).get_context_data(**kwargs)
        context['ownership'] =  self.ownership
        return context

    def get_permission_required(self):
        item_class_name = self.item_type.model
        item_app_label = self.item_type.app_label
        return [f'{item_app_label}.maintain_ownerships_for_{item_class_name}']


class UpdateCatalogueLinkView(MembershipRequiredMixin, CatalogueMixin, ItemMixin, OwnershipCatalogueLinkMixin, PermissionRequiredMixin, UpdateView):
    template_name = "inventory/catalogue_adjust_link.html"
    fields = ['note', 'added_since']

    def get_object(self, queryset=None):
        # Assure that the ownership and item are linked correctly
        return self.ownership

    def get_success_url(self):
        return reverse("inventory:catalogue_item_links",
                       kwargs={'type_id':self.item_type, 'item_id':self.item.id})


class LinkActivationStateView(MembershipRequiredMixin, CatalogueMixin, ItemMixin, OwnershipCatalogueLinkMixin, PermissionRequiredMixin, FormView):
    http_method_names = ['post']
    # Note: Set correct form_class in as_view url init_kwargs argument

    def get_form_kwargs(self):
        form_kwargs = super(LinkActivationStateView, self).get_form_kwargs()
        form_kwargs['ownership'] = self.ownership
        return form_kwargs

    def get_success_url(self):
        return reverse("inventory:catalogue_item_links",
                       kwargs={'type_id':self.item_type, 'item_id':self.item.id})

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f"{self.ownership.content_object} has been marked as taken home")
        return super(LinkActivationStateView, self).form_valid(form)

    def form_invalid(self, form):
        message = f"This action was not possible: {form.non_field_errors()[0]}"
        messages.error(self.request, message)
        return HttpResponseRedirect(self.get_success_url())


class LinkDeletionView(MembershipRequiredMixin, CatalogueMixin, ItemMixin, OwnershipCatalogueLinkMixin, PermissionRequiredMixin, FormView):
    template_name = "inventory/catalogue_delete_link.html"
    form_class = DeleteOwnershipForm

    def get_form_kwargs(self):
        form_kwargs = super(LinkDeletionView, self).get_form_kwargs()
        form_kwargs['ownership'] = self.ownership
        return form_kwargs

    def get_success_url(self):
        return reverse("inventory:catalogue_item_links",
                       kwargs={'type_id':self.item_type, 'item_id':self.item.id})

    def form_valid(self, form):
        messages.success(self.request, f"{self.ownership} has been removed")
        form.delete_link()
        return super(LinkDeletionView, self).form_valid(form)

    def form_invalid(self, form):
        message = f"This action was not possible: {form.non_field_errors()[0]}"
        messages.error(self.request, message)
        return HttpResponseRedirect(self.get_success_url())
