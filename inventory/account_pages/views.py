from django.contrib import messages
from django.http.response import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.edit import FormView

from membership_file.util import MembershipRequiredMixin

from inventory.models import Ownership, Item
from inventory.forms import *
from inventory.views import OwnershipMixin

from user_interaction.accountcollective import AccountViewMixin


__all__ = ["MemberItemsOverview", "MemberItemRemovalFormView", "MemberItemLoanFormView", "MemberOwnershipAlterView"]


class MemberItemsOverview(AccountViewMixin, ListView):
    template_name = "inventory/account_pages/inventory/membership_inventory.html"
    context_object_name = "ownerships"

    def get_queryset(self):
        return Ownership.objects.filter(member=self.request.member).filter(is_active=True)

    def get_context_data(self, *args, **kwargs):
        context = super(MemberItemsOverview, self).get_context_data(*args, **kwargs)
        # Get items previously stored at the associatoin
        context[self.context_object_name + "_history"] = Ownership.objects.filter(member=self.request.member).filter(
            is_active=False
        )
        return context


class MemberItemRemovalFormView(AccountViewMixin, OwnershipMixin, FormView):
    template_name = "inventory/account_pages/inventory/membership_take_home.html"
    form_class = OwnershipRemovalForm
    success_url = reverse_lazy("account:inventory:member_items")

    def get_form_kwargs(self):
        kwargs = super(MemberItemRemovalFormView, self).get_form_kwargs()
        kwargs["ownership"] = self.ownership
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


class MemberItemLoanFormView(AccountViewMixin, OwnershipMixin, FormView):
    template_name = "inventory/account_pages/inventory/membership_loan_out.html"
    form_class = OwnershipActivationForm
    success_url = reverse_lazy("account:inventory:member_items")

    def get_form_kwargs(self):
        kwargs = super(MemberItemLoanFormView, self).get_form_kwargs()
        kwargs["ownership"] = self.ownership
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


class MemberOwnershipAlterView(AccountViewMixin, OwnershipMixin, FormView):
    template_name = "inventory/account_pages/inventory/membership_adjust_note.html"
    form_class = OwnershipNoteForm
    success_url = reverse_lazy("account:inventory:member_items")

    def get_form_kwargs(self):
        kwargs = super(MemberOwnershipAlterView, self).get_form_kwargs()
        kwargs["instance"] = self.ownership
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f"Your version of {self.ownership.content_object} has been updated")
        return super(MemberOwnershipAlterView, self).form_valid(form)
