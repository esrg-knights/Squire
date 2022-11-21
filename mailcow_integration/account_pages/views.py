from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from dynamic_preferences.forms import PreferenceForm
from dynamic_preferences.users.forms import user_preference_form_builder

from user_interaction.accountcollective import AccountViewMixin


class EmailPreferencesChangeView(AccountViewMixin, FormView):
    """ View for updating mail preferences """
    template_name = 'mailcow_integration/account_pages/mail_preferences_change_form.html'
    success_url = reverse_lazy('account:email_preferences')

    def get_form_class(self):
        return user_preference_form_builder(instance=self.request.user, section='mail')

    def form_valid(self, form: PreferenceForm):
        message = _("Your mail preferences have been updated!")
        messages.success(self.request, message)
        form.update_preferences()
        form = self.get_form()
        return super().form_valid(form)
