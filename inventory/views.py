from django.http.response import HttpResponseForbidden, HttpResponseRedirect
from django.contrib import messages
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import FormView, FormMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404

from inventory.models import BoardGame, Ownership
from inventory.forms import *


class BoardgameView(ListView):
    template_name = "inventory/boardgames_overview.html"
    context_object_name = 'boardgames'

    paginate_by = 10

    def get_queryset(self):
        return BoardGame.objects.get_all_in_possession()


class MemberItemsOverview(ListView):
    template_name = "inventory/membership_inventory.html"
    context_object_name = 'ownerships'

    def get_queryset(self):
        return Ownership.objects.filter(member=self.request.user.member).filter(is_active=True)

    def get_context_data(self, *args, **kwargs):
        context = super(MemberItemsOverview, self).get_context_data(*args, **kwargs)
        context[self.context_object_name+'_history'] = Ownership.objects.\
            filter(member=self.request.user.member).\
            filter(is_active=False)
        return context


class OwnershipMixin:
    ownership = None

    def dispatch(self, request, *args, **kwargs):
        self.ownership = get_object_or_404(Ownership, id=self.kwargs['ownership_id'])
        if not self.can_access():
            return HttpResponseForbidden()

        return super(OwnershipMixin, self).dispatch(request, *args, **kwargs)

    def can_access(self):
        if self.ownership.member:
            if self.request.user.member != self.ownership.member:
                return False
        else:
            if self.ownership.group not in self.request.user.groups.all():
                return False
        return True

    def get_context_data(self, **kwargs):
        context = super(OwnershipMixin, self).get_context_data(**kwargs)
        context['ownership'] = self.ownership
        return context


class MemberItemRemovalFormView(OwnershipMixin, FormView):
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
        return HttpResponseRedirect(self.get_success_url())


class MemberItemLoanFormView(OwnershipMixin, FormView):
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
        return HttpResponseRedirect(self.get_success_url())


class MemberOwnershipAlterView(OwnershipMixin, FormView):
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
