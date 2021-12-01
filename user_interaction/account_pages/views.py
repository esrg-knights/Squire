from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.views.generic import TemplateView, FormView
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from dynamic_preferences.users.forms import user_preference_form_builder

from core.forms import PasswordChangeForm
from user_interaction.account_pages.mixins import AccountViewMixin


class SiteAccountView(AccountViewMixin, TemplateView):
    template_name = "user_interaction/account_pages/site_account_page.html"
    selected_tab_name = 'tab_account_info'


class AccountPasswordChangeView(AccountViewMixin, PasswordChangeView):
    template_name = "user_interaction/account_pages/password_change_form.html"
    success_url = reverse_lazy("account:site_account")
    selected_tab_name = "tab_account_info"
    form_class = PasswordChangeForm

    def form_valid(self, form):
        result = super(AccountPasswordChangeView, self).form_valid(form)
        messages.success(self.request, _("Password succesfully changed"))
        return result


class LayoutPreferencesUpdateView(AccountViewMixin, FormView):
    """ View for updating user preferences """
    template_name = 'user_interaction/preferences_change_form.html'
    success_url = reverse_lazy('account:site_account')
    selected_tab_name = 'tab_account_info'

    def get_form_class(self):
        return user_preference_form_builder(instance=self.request.user, section='layout')

    def form_valid(self, form):
        message = _("Your preferences have been updated!")
        messages.success(self.request, message)
        form.update_preferences()
        form = self.get_form()
        return super().form_valid(form)
