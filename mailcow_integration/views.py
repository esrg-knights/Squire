from enum import Enum
from typing import Dict, List, Optional

from django.apps import apps
from django.conf import settings
from django.views.generic import TemplateView

from mailcow_integration.api.exceptions import MailcowAPIAccessDenied, MailcowAPIReadWriteAccessDenied, MailcowAuthException, MailcowException
from mailcow_integration.api.interface.alias import MailcowAlias
from mailcow_integration.squire_mailcow import SquireMailcowManager
from membership_file.models import Member

from utils.views import SuperUserRequiredMixin

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

    # TODO: Placeholder; move elsewhere
    def _get_subscribed_member_addresses(self, alias_address: str) -> List[str]:
        """ TODO """
        # TODO: Support opt-outs for specific lists
        return list(Member.objects.filter_active().order_by('email').values_list('email', flat=True))

    def _verify_aliasses_exist(self, alias_addresses: List[str], all_aliases: List[MailcowAlias], public_comment: str) -> Dict[str, AliasStatus]:
        """ TODO """
        results = {
            alias: {
                'alias': None,
                'status': AliasStatus.MISSING.name,
                'squire_subscribers': self._get_subscribed_member_addresses(alias),
            }
            for alias in alias_addresses
        }

        for alias in all_aliases:
            if alias.address in alias_addresses:
                if alias.public_comment != public_comment:
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.NOT_MANAGED_BY_SQUIRE.name})
                elif alias.goto != results[alias.address]['squire_subscribers']:
                    # Note: Lists are sorted
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
                context['member_aliases'] = self._verify_aliasses_exist(settings.INTERNAL_MEMBERS_ALIAS, aliases, self.mailcow_client.ALIAS_MEMBERS_PUBLIC_COMMENT)


                # TODO: committee-aliases






        return context
