from enum import Enum
from typing import Dict, List, Optional

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView, FormView

from mailcow_integration.api.exceptions import MailcowAPIAccessDenied, MailcowAPIReadWriteAccessDenied, MailcowAuthException, MailcowException
from mailcow_integration.api.interface.alias import MailcowAlias
from mailcow_integration.squire_mailcow import SquireMailcowManager
from membership_file.models import Member

from utils.views import PostOnlyFormViewMixin, SuperUserRequiredMixin

# apps.get_app_config("mailcow_integration")

class AliasStatus(Enum):
    """ TODO """
    VALID = 0
    MISSING = 1
    NOT_MANAGED_BY_SQUIRE = 2
    OUTDATED = 3

class MailcowStatusView(SuperUserRequiredMixin, TemplateView):
    """ TODO """
    template_name = "mailcow_integration/status.html"

    def __init__(self, *args, **kwargs) -> None:
        config = apps.get_app_config("mailcow_integration")
        self.mailcow_client: Optional[SquireMailcowManager] = config.mailcow_client

    def _verify_aliasses_exist(self, alias_addresses: Dict[str, Dict], all_aliases: List[MailcowAlias], public_comment: str) -> Dict[str, Dict]:
        """ TODO """
        self.mailcow_client: SquireMailcowManager
        active_members = self.mailcow_client.get_active_members()
        results = {
            alias_config['address']: {
                'alias': None,
                'status': AliasStatus.MISSING.name,
                'squire_subscribers': self.mailcow_client.get_subscribed_members(
                    active_members,
                    alias_id,
                    default=alias_config['default_opt']
                ),
                'id': alias_id,
                'description': alias_config['description'],
                'internal': alias_config['internal'],
                'allow_opt_out': alias_config['allow_opt_out'],
            }
            for alias_id, alias_config in alias_addresses.items()
        }

        for alias in all_aliases:
            if alias.address in results.keys():
                if alias.public_comment != public_comment:
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.NOT_MANAGED_BY_SQUIRE.name})
                elif alias.goto != list(results[alias.address]['squire_subscribers'].values_list('email', flat=True)):
                    # Note: Lists are sorted
                    # TODO: verify internal-status
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.OUTDATED.name})
                else:
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.VALID.name})

        return results

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.mailcow_client is not None:
            context['mailcow_host'] = self.mailcow_client._client.host

            try:
                aliases = self.mailcow_client.get_all_aliases()
                # TODO: Fetch internal status
            except MailcowAuthException as e:
                context['error'] = "No valid API key set."
            except MailcowAPIReadWriteAccessDenied as e:
                context['error'] = "API key only allows access to read operations, not write."
            except MailcowAPIAccessDenied as e:
                context['error'] = "IP address is not whitelisted in the Mailcow admin."
            except MailcowException as e:
                context['error'] = print(", ".join(e.args))
            else:
                context['member_aliases'] = self._verify_aliasses_exist(settings.MEMBER_ALIASES, aliases, self.mailcow_client.ALIAS_MEMBERS_PUBLIC_COMMENT)


                # TODO: committee-aliases

                # TODO: List "[Managed by Squire]" aliases that are no longer in use (to allow cleanup)

        return context

    def post(self, request, *args, **kwargs):
        if self.request.POST.get("alias_type", None) == "members":
            self.mailcow_client.update_member_aliases()
            messages.success(self.request, "Member aliases updated.")
        else:
            # TODO: Update user aliases
            messages.success(self.request, "Committee aliases updated.")
            pass

        return HttpResponseRedirect(self.request.get_full_path())
