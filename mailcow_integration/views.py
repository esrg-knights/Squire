from enum import Enum
from typing import Dict, List, Optional

from django.apps import apps
from django.conf import settings
from django.db.models import F, Q, Value, ExpressionWrapper, BooleanField
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView

from mailcow_integration.api.exceptions import MailcowAPIAccessDenied, MailcowAPIReadWriteAccessDenied, MailcowAuthException, MailcowException
from mailcow_integration.api.interface.alias import MailcowAlias
from mailcow_integration.squire_mailcow import SquireMailcowManager

from utils.views import SuperUserRequiredMixin

from committees.models import AssociationGroup

class AliasStatus(Enum):
    """ Aliases that should exist according to Squire may not be in sync with those in Mailcow.
        This Enum indicates the disparity between the two.
    """
    VALID = 0 # Squire and mailcow are in sync
    MISSING = 1 # Alias is not in Mailcow, but should exist
    NOT_MANAGED_BY_SQUIRE = 2 # Alias is in Mailcow, but does not have a public comment indicating it is managed by Squire
    OUTDATED = 3 # Alias goto-addresses do not match up with Squire

class MailcowStatusView(SuperUserRequiredMixin, TemplateView):
    """ An overview of aliases managed by Squire. Connects to the Mailcow API to determine whether
        such aliases are considered up-to-date. Also allows forced updates of each alias.
    """
    template_name = "mailcow_integration/status.html"

    def __init__(self, *args, **kwargs) -> None:
        config = apps.get_app_config("mailcow_integration")
        self.mailcow_manager: Optional[SquireMailcowManager] = config.mailcow_client

    def _verify_aliasses_exist(self, alias_configs: Dict[str, Dict], mailcow_aliases: List[MailcowAlias], public_comment: str) -> Dict[str, Dict]:
        """ Verifies the status of a list of alias configs (as per mailcowconfig.json) and
            their corresponding aliases in Mailcow. Each alias should match `public_comment`
            in order for Squire to know that it should manage it.
            The return value of this method is used to format the template of this view.
        """
        self.mailcow_manager: SquireMailcowManager
        active_members = self.mailcow_manager.get_active_members()
        results = {
            alias_config['address']: {
                'alias': None,
                'status': AliasStatus.MISSING.name,
                'squire_subscribers': self.mailcow_manager.get_subscribed_members(
                    active_members,
                    alias_id,
                    default=alias_config['default_opt']
                ).annotate(
                    # Indicate that emails are ignored
                    has_invalid_email=ExpressionWrapper(Q(email__in=self.mailcow_manager._member_alias_addresses), output_field=BooleanField())
                ),
                'id': alias_id,
                'description': alias_config['description'],
                'internal': alias_config['internal'],
                'allow_opt_out': alias_config['allow_opt_out'],
            }
            for alias_id, alias_config in alias_configs.items()
        }

        # Verify that each of our aliases actually exists in Mailcow
        for alias in mailcow_aliases:
            if alias.address in results.keys():
                if alias.public_comment != public_comment:
                    # Public comment of the alias does not indicate it is managed by Squire
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.NOT_MANAGED_BY_SQUIRE.name})
                elif alias.goto != self.mailcow_manager.clean_member_emails(results[alias.address]['squire_subscribers']):
                    # Subscribers are out of date
                    #   Note: Lists are sorted
                    # TODO: verify internal-status
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.OUTDATED.name})
                else:
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.VALID.name})
        return results

    def _verify_committee_aliases(self, mailcow_aliases: List[MailcowAlias], public_comment: str) -> Dict:
        """ TODO """
        results = {
            assoc_group.contact_email: {
                'alias': None,
                'status': AliasStatus.MISSING.name,
                'squire_subscribers': assoc_group.members.filter_active().order_by('email'),
                'id': assoc_group.id,
                'description': assoc_group.site_group.name,
                'internal': False,
                'allow_opt_out': False,
            }
            for assoc_group in self.mailcow_manager.get_alias_committees()
        }

        # Verify that each of our aliases actually exists in Mailcow
        for alias in mailcow_aliases:
            if alias.address in results.keys():
                if alias.public_comment != public_comment:
                    # Public comment of the alias does not indicate it is managed by Squire
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.NOT_MANAGED_BY_SQUIRE.name})
                elif alias.goto != self.mailcow_manager.clean_member_emails(results[alias.address]['squire_subscribers']):
                    # Subscribers are out of date
                    #   Note: Lists are sorted
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.OUTDATED.name})
                else:
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.VALID.name})
        return results


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.mailcow_manager is not None:
            context['mailcow_host'] = self.mailcow_manager.mailcow_host

            try:
                aliases = list(self.mailcow_manager.get_alias_all(use_cache=False))
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
                context['member_aliases'] = self._verify_aliasses_exist(settings.MEMBER_ALIASES, aliases, self.mailcow_manager.ALIAS_MEMBERS_PUBLIC_COMMENT)
                context['committee_aliases'] = self._verify_committee_aliases(aliases, self.mailcow_manager.ALIAS_COMMITTEE_PUBLIC_COMMENT)

                # TODO: committee-aliases

                # TODO: List "[Managed by Squire]" aliases that are no longer in use (to allow cleanup)

        return context

    def post(self, request, *args, **kwargs):
        # One of the update buttons was pressed.
        if self.request.POST.get("alias_type", None) == "members":
            # Update all member aliases
            self.mailcow_manager.update_member_aliases()
            messages.success(self.request, "Member aliases updated.")
        else:
            # Update all committee aliases
            # TODO: Update user aliases
            self.mailcow_manager.update_committee_aliases()
            messages.success(self.request, "Committee aliases updated.")

        return HttpResponseRedirect(self.request.get_full_path())
