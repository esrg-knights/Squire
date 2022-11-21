from django.apps import apps
from django.contrib import messages
from django.forms import BooleanField
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from dynamic_preferences.forms import PreferenceForm
from dynamic_preferences.users.forms import user_preference_form_builder
from mailcow_integration.squire_mailcow import SquireMailcowManager

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
        print(form.initial)
        form.update_preferences()

        has_any_changes = False
        for name, field in form.fields.items():
            field: BooleanField
            if field.has_changed(field.initial, form.cleaned_data[name]):
                has_any_changes = True
                break

        if has_any_changes:
            print("updating member aliases (user form)")
            # Update mailcow alias;
            #   Mailcow client must be set up if this view can be accessed
            config = apps.get_app_config("mailcow_integration")
            mailcow_client: SquireMailcowManager = config.mailcow_client
            mailcow_client.update_member_aliases()

        form = self.get_form()
        return super().form_valid(form)
