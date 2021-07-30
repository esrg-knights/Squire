from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http.response import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import FormView, UpdateView, CreateView

from committees.views import GroupMixin
from membership_file.util import MembershipRequiredMixin
from utils.views import SearchFormMixin

from inventory.models import BoardGame, Ownership
from inventory.forms import *


class BoardGameView(ListView):
    template_name = "inventory/boardgames_overview.html"
    context_object_name = 'boardgames'

    paginate_by = 10

    def get_queryset(self):
        return BoardGame.objects.get_all_in_possession()


class MemberItemsOverview(MembershipRequiredMixin, ListView):
    template_name = "inventory/membership_inventory.html"
    context_object_name = 'ownerships'

    def get_queryset(self):
        return Ownership.objects.filter(member=self.request.user.member).filter(is_active=True)

    def get_context_data(self, *args, **kwargs):
        context = super(MemberItemsOverview, self).get_context_data(*args, **kwargs)
        # Get items previously stored at the associatoin
        context[self.context_object_name+'_history'] = Ownership.objects.\
            filter(member=self.request.user.member).\
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
            if self.request.user.member == self.ownership.member:
                return
        elif self.allow_access_through_group:
            if self.ownership.group in self.request.user.groups.all():
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
###############   Groups / Committees   ###################
###########################################################


class GroupItemsOverview(GroupMixin, SearchFormMixin, ListView):
    template_name = "inventory/committee_inventory.html"
    context_object_name = 'ownerships'
    search_form_class = FilterOwnershipThroughRelatedItems

    def get_queryset(self):
        ownerships = Ownership.objects.filter(group=self.group).filter(is_active=True)
        return self.filter_data(ownerships)

    def get_context_data(self, **kwargs):
        # Set a list of availlable content types
        # Used for url creation to add-item pages
        addable_item_types = [BoardGame]
        content_types = []
        for content_type in addable_item_types:
            content_types.append(ContentType.objects.get_for_model(content_type))

        return super(GroupItemsOverview, self).get_context_data(
            content_types=content_types,
            **kwargs,
        )


class GroupItemLinkUpdateView(GroupMixin, OwnershipMixin, UpdateView):
    template_name = "inventory/committee_link_edit.html"
    model = Ownership
    fields = ['note', 'added_since']
    allow_access_through_group = True

    def get_object(self, queryset=None):
        return self.ownership

    def form_valid(self, form):
        messages.success(self.request, f"Link data has been updated")
        return super(GroupItemLinkUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy("inventory:committee_items", kwargs={'group_id': self.group.id})



###########################################################
###############        Catalogue        ###################
###########################################################


class CatalogueMixin:
    """ Mixin that stores the retrieved item type from the url type_id keyword """
    item_type = None    # Item item for this catalogue

    def dispatch(self, request, *args, **kwargs):
        try:
            self.item_type = ContentType.objects.get_for_id(self.kwargs['type_id'])
        except ContentType.DoesNotExist:
            raise Http404

        return super(CatalogueMixin, self).dispatch(request, *args, **kwargs)

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
    filter_field_name = 'name'

    @property
    def model(self):
        # model as attribute is called by the list queryset
        # This patch is needed to let listview catalogue and searchform work
        return self.item_type.model_class()

    def get_context_data(self, *args, **kwargs):
        context = super(TypeCatalogue, self).get_context_data(*args, **kwargs)

        item_class_name = slugify(self.item_type.model_class().__name__)
        context.update({
            'can_add_to_group': self.request.user.has_perm(f'inventory.can_add_{item_class_name}_for_group'),
            'can_add_to_member': self.request.user.has_perm(f'inventory.can_add_{item_class_name}_for_member'),
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
                           PermissionRequiredMixin, CreateView):
    form_class = AddOwnershipCommitteeLinkForm

    def get_permission_required(self):
        item_class_name = slugify(self.item_type.model_class().__name__)
        return [f'inventory.can_add_{item_class_name}_for_group']

    def get_success_url(self):
        # Go back to the committee page
        return reverse_lazy("inventory:committee_items", kwargs={'group_id': self.object.group.id})


class AddLinkMemberView(MembershipRequiredMixin, CatalogueMixin, ItemMixin, AddLinkFormMixin,
                        PermissionRequiredMixin, FormView):
    form_class = AddOwnershipMemberLinkForm

    def get_permission_required(self):
        item_class_name = slugify(self.item_type.model_class().__name__)
        return [f'inventory.can_add_{item_class_name}_for_member']

    def get_success_url(self):
        # Go back to the catalogue page
        return reverse_lazy("inventory:catalogue", kwargs={'type_id': self.item_type.id})

