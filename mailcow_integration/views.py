from enum import Enum
from typing import Dict, List, Optional

from django.apps import apps
from django.conf import settings
from django.db.models import F, Q, Value, ExpressionWrapper, BooleanField
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.views.generic import TemplateView

from mailcow_integration.api.exceptions import MailcowAPIAccessDenied, MailcowAPIReadWriteAccessDenied, MailcowAuthException, MailcowException
from mailcow_integration.api.interface.alias import MailcowAlias
from mailcow_integration.api.interface.mailbox import MailcowMailbox
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
    RESERVED = 4 # Alias already reserved for a member-alias, but a committee has it as their contact info
    MAILBOX = 5 # Mailbox with the same name already exists; not managed by Squire

class MailcowStatusView(SuperUserRequiredMixin, TemplateView):
    """ An overview of aliases managed by Squire. Connects to the Mailcow API to determine whether
        such aliases are considered up-to-date. Also allows forced updates of each alias.
    """
    template_name = "mailcow_integration/status.html"

    def __init__(self, *args, **kwargs) -> None:
        config = apps.get_app_config("mailcow_integration")
        self.mailcow_manager: Optional[SquireMailcowManager] = config.mailcow_client

    def _get_alias_exposure_routes(self, alias: str, aliases: List[MailcowAlias], mailboxes: List[MailcowMailbox],
            alias_configs: Dict[str, Dict]) -> List[List[str]]:
        """ TODO """
        routes: List[List[str]] = []
        for mc_alias in aliases:
            if alias in mc_alias.goto:
                if not next((config['internal'] for config in alias_configs.values() if config['address'] == mc_alias.address), False):
                    # Exposed
                    routes.append([mc_alias.address])
                else:
                    # Other internal address might be exposed
                    for route in self._get_alias_exposure_routes(mc_alias.address, aliases, mailboxes, alias_configs):
                        route.append(mc_alias.address)
                        routes.append(route)
        return routes

    def _verify_aliasses_exist(self, alias_configs: Dict[str, Dict], mailcow_aliases: List[MailcowAlias], mailcow_mailboxes: List[MailcowMailbox], public_comment: str) -> Dict[str, Dict]:
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
                'squire_edit_url': None,
                'exposure_routes': (
                    self._get_alias_exposure_routes(alias_config['address'], mailcow_aliases, mailcow_mailboxes, alias_configs)
                    if alias_config['internal']
                    else []
                )
            }
            for alias_id, alias_config in alias_configs.items()
        }

        # Verify that each of our aliases actually exists in Mailcow
        for alias in mailcow_aliases:
            if alias.address in results.keys():
                if alias.public_comment != public_comment:
                    # Public comment of the alias does not indicate it is managed by Squire
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.NOT_MANAGED_BY_SQUIRE.name})
                elif alias.goto != self.mailcow_manager.clean_alias_emails(results[alias.address]['squire_subscribers']) + [settings.MEMBER_ALIAS_ARCHIVE_ADDRESS]:
                    # Subscribers are out of date
                    #   Note: Lists are sorted
                    # TODO: verify internal-status
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.OUTDATED.name})
                else:
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.VALID.name})

        # Find mailboxes with the same name
        for mailbox in mailcow_mailboxes:
            if mailbox.username in results:
                results[mailbox.username].update({'mailbox': mailbox, 'status': AliasStatus.MAILBOX.name})

        return results

    def _verify_committee_aliases(self, mailcow_aliases: List[MailcowAlias], mailcow_mailboxes: List[MailcowMailbox], public_comment: str) -> Dict:
        """ TODO """
        results = {
            assoc_group.contact_email: {
                'alias': None,
                'status': AliasStatus.MISSING.name if not assoc_group.has_invalid_email else AliasStatus.RESERVED.name,
                'squire_subscribers': assoc_group.members.filter_active().order_by('email')\
                    .annotate(
                        # Indicate that emails are ignored
                        has_invalid_email=ExpressionWrapper(Q(email__in=self.mailcow_manager._member_alias_addresses), output_field=BooleanField())
                ),
                'id': assoc_group.id,
                'description': format_html("{} ({}): {}", assoc_group.site_group.name, assoc_group.get_type_display(), assoc_group.short_description),
                'internal': False,
                'allow_opt_out': True, # Cannot actually opt out; tricking the template here
                'squire_edit_url': reverse("admin:committees_associationgroup_change", args=[assoc_group.id]),
            }
            for assoc_group in self.mailcow_manager.get_alias_committees().annotate(
                has_invalid_email=ExpressionWrapper(Q(contact_email__in=self.mailcow_manager._member_alias_addresses), output_field=BooleanField())
            )
        }

        # Verify that each of our aliases actually exists in Mailcow
        for alias in mailcow_aliases:
            if alias.address in results.keys():
                if results[alias.address]['status'] == AliasStatus.RESERVED.name:
                    results[alias.address].update({'alias': alias})
                elif alias.public_comment != public_comment:
                    # Public comment of the alias does not indicate it is managed by Squire
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.NOT_MANAGED_BY_SQUIRE.name})
                elif alias.goto != self.mailcow_manager.clean_alias_emails(results[alias.address]['squire_subscribers']) + [settings.COMMITTEE_ALIAS_ARCHIVE_ADDRESS]:
                    # Subscribers are out of date
                    #   Note: Lists are sorted
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.OUTDATED.name})
                else:
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.VALID.name})

        for mailbox in mailcow_mailboxes:
            if mailbox.username in results:
                results[mailbox.username].update({'mailbox': mailbox, 'status': AliasStatus.MAILBOX.name})

        return results

    def _verify_committee_aliases(self, mailcow_aliases: List[MailcowAlias], mailcow_mailboxes: List[MailcowMailbox], public_comment: str) -> Dict:
        """ TODO """
        results = {
            assoc_group.contact_email: {
                'alias': None,
                'status': AliasStatus.MISSING.name if not assoc_group.has_invalid_email else AliasStatus.RESERVED.name,
                'squire_subscribers': assoc_group.members.filter_active().order_by('email')\
                    .annotate(
                        # Indicate that emails are ignored
                        has_invalid_email=ExpressionWrapper(Q(email__in=self.mailcow_manager._member_alias_addresses), output_field=BooleanField())
                ),
                'id': assoc_group.id,
                'description': format_html("{} ({}): {}", assoc_group.site_group.name, assoc_group.get_type_display(), assoc_group.short_description),
                'internal': False,
                'allow_opt_out': True, # Cannot actually opt out; tricking the template here
                'squire_edit_url': reverse("admin:committees_associationgroup_change", args=[assoc_group.id]),
            }
            for assoc_group in self.mailcow_manager.get_alias_committees().annotate(
                has_invalid_email=ExpressionWrapper(Q(contact_email__in=self.mailcow_manager._member_alias_addresses), output_field=BooleanField())
            )
        }

        # Verify that each of our aliases actually exists in Mailcow
        for alias in mailcow_aliases:
            if alias.address in results.keys():
                if results[alias.address]['status'] == AliasStatus.RESERVED.name:
                    results[alias.address].update({'alias': alias})
                elif alias.public_comment != public_comment:
                    # Public comment of the alias does not indicate it is managed by Squire
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.NOT_MANAGED_BY_SQUIRE.name})
                elif alias.goto != self.mailcow_manager.clean_alias_emails(results[alias.address]['squire_subscribers']) + [settings.COMMITTEE_ALIAS_ARCHIVE_ADDRESS]:
                    # Subscribers are out of date
                    #   Note: Lists are sorted
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.OUTDATED.name})
                else:
                    results[alias.address].update({'alias': alias, 'status': AliasStatus.VALID.name})

        for mailbox in mailcow_mailboxes:
            if mailbox.username in results:
                results[mailbox.username].update({'mailbox': mailbox, 'status': AliasStatus.MAILBOX.name})

        return results

    def _find_unused_squire_comments(self, mailcow_aliases: List[MailcowAlias], member_aliases, committee_aliases):
        """ TODO """
        used_addresses = list(member_aliases.keys()) + list(committee_aliases.keys())
        return list(
            # Ignore addresses that we still need
            filter(lambda alias: alias.address not in used_addresses,
                # Only include addresses starting with the "[MANAGED BY SQUIRE]" indicator
                filter(lambda alias:
                    (alias.public_comment or "").startswith(self.mailcow_manager.SQUIRE_MANAGE_INDICATOR),
                    mailcow_aliases
                )
        ))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.mailcow_manager is not None:
            context['mailcow_host'] = self.mailcow_manager.mailcow_host

            try:
                aliases = list(self.mailcow_manager.get_alias_all(use_cache=False))
                mailboxes = list(self.mailcow_manager.get_mailbox_all(use_cache=False))
                # TODO: Fetch internal status
            except MailcowAuthException as e:
                context['error'] = "No valid API key set."
            except MailcowAPIReadWriteAccessDenied as e:
                context['error'] = "API key only allows access to read operations, not write."
            except MailcowAPIAccessDenied as e:
                ip = str(e).rpartition(" ")[2]
                context['error'] = f"IP address is not whitelisted in the Mailcow admin: {ip}"
            except MailcowException as e:
                context['error'] = print(", ".join(e.args))
            else:
                context['member_aliases'] = self._verify_aliasses_exist(settings.MEMBER_ALIASES, aliases, mailboxes, self.mailcow_manager.ALIAS_MEMBERS_PUBLIC_COMMENT)
                context['committee_aliases'] = self._verify_committee_aliases(aliases, mailboxes, self.mailcow_manager.ALIAS_COMMITTEE_PUBLIC_COMMENT)
                context['unused_squire_comments'] = self._find_unused_squire_comments(aliases, context['member_aliases'], context['committee_aliases'])
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
