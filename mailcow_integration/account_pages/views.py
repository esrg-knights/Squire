from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.views.generic import TemplateView, FormView, UpdateView
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from dynamic_preferences.users.forms import user_preference_form_builder
from dynamic_preferences.forms import PreferenceForm

from user_interaction.accountcollective import AccountViewMixin

class EmailPreferencesChangeView(AccountViewMixin, FormView):
    """ View for updating mail preferences """
    template_name = 'mailcow_integration/account_pages/mail_preferences_change_form.html'
    success_url = reverse_lazy('account:email_preferences')

    def get_form_class(self):
        return user_preference_form_builder(instance=self.request.user, section='mail')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # Add additional info to labels and/or disable options based on config
        member_aliases = settings.MEMBER_ALIASES
        for boundfield in form:
            # Find relevant config
            alias_id = boundfield.auto_id.split("__")[1]
            alias_config = member_aliases[alias_id]
            label_elements = ["{}"]

            # Disable form field if opt-outs are disallowed
            if not alias_config['allow_opt_out']:
                boundfield.field.disabled = True
                label_elements.append('<span class="badge badge-warning badge-pill"><i class="fas fa-lock"></i> Cannot opt-out</span>')

            # Explicitly mark non-internal aliases as "public"
            if not alias_config['internal']:
                label_elements.append('<span class="badge badge-primary badge-pill"><i class="fas fas fa-globe"></i> Public</span>')

            # Properly escape HTML
            boundfield.label = format_html(
                ' '.join(label_elements),
                boundfield.label
            )
        return form

    def form_valid(self, form: PreferenceForm):
        message = _("Your mail preferences have been updated!")
        messages.success(self.request, message)
        form.update_preferences()
        form = self.get_form()
        return super().form_valid(form)
