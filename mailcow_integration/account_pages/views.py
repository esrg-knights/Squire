from typing import Any, Dict, Type
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from dynamic_preferences.users.forms import preference_form_builder
from mailcow_integration.account_pages.forms import MemberMailPreferencesForm
from mailcow_integration.squire_mailcow import get_mailcow_manager

from user_interaction.accountcollective import AccountViewMixin


class EmailPreferencesChangeView(FormView):
    """View for updating mail preferences"""

    template_name = "mailcow_integration/account_pages/mail_preferences_change_form.html"
    success_url = reverse_lazy("account:email_preferences")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.mailcow_manager = get_mailcow_manager()

    def get_form_class(self) -> Type[MemberMailPreferencesForm]:
        return preference_form_builder(MemberMailPreferencesForm, instance=self.request.user, section="mail")

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["mailcow_manager"] = self.mailcow_manager
        return kwargs

    def form_valid(self, form: MemberMailPreferencesForm):
        message = _("Your mail preferences have been updated!")
        # Updating preferences is done in form_valid, as suggested by the docs:
        #   https://django-dynamic-preferences.readthedocs.io/en/latest/quickstart.html#form-builder-with-djangoformview
        form.update_preferences()
        messages.success(self.request, message)

        form = self.get_form()
        return super().form_valid(form)


class TabbedEmailPreferencesChangeView(AccountViewMixin, EmailPreferencesChangeView):
    """EmailPreferencesView for usage in registry tabs"""
