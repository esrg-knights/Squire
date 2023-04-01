from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, TypedDict

from django.conf import settings
from django.db.models import Q, ExpressionWrapper, BooleanField, QuerySet
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.views.generic import TemplateView

from mailcow_integration.api.exceptions import MailcowAPIAccessDenied, MailcowAPIReadWriteAccessDenied, MailcowAuthException, MailcowException
from mailcow_integration.api.interface.alias import MailcowAlias
from mailcow_integration.api.interface.base import MailcowAPIResponse
from mailcow_integration.api.interface.mailbox import MailcowMailbox
from mailcow_integration.dynamic_preferences_registry import alias_address_to_id
from mailcow_integration.squire_mailcow import AliasCategory, SquireMailcowManager, get_mailcow_manager

from utils.views import SuperUserRequiredMixin

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
    ORPHAN = 6 # Alias is not needed by Squire, but existed in Mailcow

class SubscriberInfos(TypedDict):
    """ Representation of a subscriber """
    name: str
    invalid: bool

@dataclass
class AliasInfos:
    """ TODO """
    status: str
    subscribers: List[SubscriberInfos]
    address: str
    modal_id: str
    title: str
    description: str
    data: Optional[MailcowAPIResponse] = None
    internal: Optional[bool] = None
    exposure_routes: List[List[str]] = field(default_factory=list)
    allow_opt_out: Optional[bool] = None
    squire_edit_url: Optional[str] = None
    archive_addresses: List[str] = field(default_factory=list)

class MailcowStatusView(SuperUserRequiredMixin, TemplateView):
    """ An overview of aliases managed by Squire. Connects to the Mailcow API to determine whether
        such aliases are considered up-to-date. Also allows forced updates of each alias.
    """
    template_name = "mailcow_integration/status.html"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.mailcow_manager: SquireMailcowManager = get_mailcow_manager()

    def _get_alias_status(self, address: str, subscribers: QuerySet, alias_type: AliasCategory,
            aliases: List[MailcowAlias], mailboxes: List[MailcowMailbox], squire_comment: str) -> Tuple[AliasStatus, Optional[MailcowAlias], Optional[MailcowMailbox]]:
        """ TODO """
        if (alias_type != AliasCategory.MEMBER and address in settings.MEMBER_ALIASES
                or alias_type == AliasCategory.COMMITTEE and address in settings.COMMITTEE_CONFIGS['global_addresses']):
            # Address is reserved
            return AliasStatus.RESERVED, None, None

        elif mailbox := next((mailbox for mailbox in mailboxes if mailbox.username == address), None):
            # Address is already a mailbox
            return AliasStatus.MAILBOX, None, mailbox

        elif alias := next((alias for alias in aliases if alias.address == address), None):
            # Alias exists
            if alias.public_comment != squire_comment:
                # Public comment does not indicate it's managed by squire
                return AliasStatus.NOT_MANAGED_BY_SQUIRE, alias, None
            elif alias.goto != self.mailcow_manager.get_archive_adresses_for_type(alias_type, address) + self.mailcow_manager.clean_emails_flat(subscribers):
                # Alias is outdated
                return AliasStatus.OUTDATED, alias, None
            else:
                # Alias is valid
               return AliasStatus.VALID, alias, None
        else:
            # Alias does not exist
            return AliasStatus.MISSING, None, None

    def _get_alias_exposure_routes(self, address: str, aliases: List[MailcowAlias], mailboxes: List[MailcowMailbox],
            member_aliases: Dict[str, Dict]) -> List[List[str]]:
        """ TODO """
        routes: List[List[str]] = []
        for alias in aliases:
            if address in alias.goto:
                if not next((config['internal'] for member_address, config in member_aliases.items() if member_address == alias.address), False):
                    # Exposed
                    routes.append([alias.address])
                else:
                    # Other internal address might be exposed
                    for route in self._get_alias_exposure_routes(alias.address, aliases, mailboxes, member_aliases):
                        route.append(alias.address)
                        routes.append(route)
        return routes

    def _get_subscriberinfos_by_status(self, status: AliasStatus, subscribers: QuerySet,
            alias: Optional[MailcowAlias], alias_type: AliasCategory = AliasCategory.MEMBER) -> List[SubscriberInfos]:
        """ Determines how subscribers should be displayed, based on the status of the alias """
        if status == AliasStatus.NOT_MANAGED_BY_SQUIRE:
            return [{'name': addr, 'invalid': False} for addr in alias.goto]
        elif status == AliasStatus.MAILBOX or status == AliasStatus.RESERVED:
            return []
        else:
            email_field = "email"
            get_name = lambda sub: sub.get_full_name()
            if alias_type == AliasCategory.GLOBAL_COMMITTEE:
                email_field = "contact_email"
                get_name = lambda sub: f"{sub.site_group.name} ({sub.get_type_display()})"

            subscribers = subscribers.annotate(has_invalid_email=ExpressionWrapper(
                Q(**{f"{email_field}__in": self.mailcow_manager.BLOCKLISTED_EMAIL_ADDRESSES}), output_field=BooleanField()
            ))
            return [{
                'name': format_html("{} &mdash; {}", get_name(sub), getattr(sub, email_field)),
                'invalid': sub.has_invalid_email
            } for sub in subscribers]

    def _init_member_alias_list(self, aliases: List[MailcowAlias], mailboxes: List[MailcowMailbox]) -> List[AliasInfos]:
        """ TODO """
        active_members = self.mailcow_manager.get_active_members()
        infos: List[AliasInfos] = []

        for address, config in settings.MEMBER_ALIASES.items():
            subscribers = self.mailcow_manager.get_subscribed_members(
                active_members,
                address,
                default=config['default_opt']
            )
            status, alias, mailbox = self._get_alias_status(address, subscribers, AliasCategory.MEMBER,
                aliases, mailboxes, self.mailcow_manager.ALIAS_MEMBERS_PUBLIC_COMMENT)

            exposure_routes = []
            if config['internal']:
                exposure_routes = self._get_alias_exposure_routes(address, aliases, mailboxes, config)

            subscribers = self._get_subscriberinfos_by_status(status, subscribers, alias)
            info = AliasInfos(status.name, subscribers, address, alias_address_to_id(address), config['title'], config['description'],
                alias or mailbox, config['internal'], exposure_routes, config['allow_opt_out'], archive_addresses=config['archive_addresses']
            )
            infos.append(info)
        return infos

    def _init_global_committee_alias_list(self, aliases: List[MailcowAlias], mailboxes: List[MailcowMailbox]) -> List[AliasInfos]:
        """ TODO """
        infos: List[AliasInfos] = []

        for address in settings.COMMITTEE_CONFIGS["global_addresses"]:
            subscribers = self.mailcow_manager.get_alias_committees()

            status, alias, mailbox = self._get_alias_status(address, subscribers, AliasCategory.GLOBAL_COMMITTEE,
                aliases, mailboxes, self.mailcow_manager.ALIAS_GLOBAL_COMMITTEE_PUBLIC_COMMENT)

            subscribers = self._get_subscriberinfos_by_status(status, subscribers, alias, alias_type=AliasCategory.GLOBAL_COMMITTEE)
            info = AliasInfos(status.name, subscribers, address, "gc_" + alias_address_to_id(address), address,
                "Allows mailing all committees at the same time.",
                alias or mailbox, False, allow_opt_out=False, archive_addresses=settings.COMMITTEE_CONFIGS['global_archive_addresses']
            )
            infos.append(info)
        return infos

    def _init_committee_alias_list(self, aliases: List[MailcowAlias], mailboxes: List[MailcowMailbox]) -> List[AliasInfos]:
        """ TODO """
        infos: List[AliasInfos] = []

        for assoc_group in self.mailcow_manager.get_alias_committees():
            address = assoc_group.contact_email
            subscribers = assoc_group.members.filter_active().order_by('email')

            status, alias, mailbox = self._get_alias_status(address, subscribers, AliasCategory.COMMITTEE,
                aliases, mailboxes, self.mailcow_manager.ALIAS_COMMITTEE_PUBLIC_COMMENT)

            subscribers = self._get_subscriberinfos_by_status(status, subscribers, alias)
            info = AliasInfos(status.name, subscribers, address, assoc_group.id, assoc_group.site_group.name,
                format_html("{} ({}): {}", assoc_group.site_group.name, assoc_group.get_type_display(), assoc_group.short_description),
                alias or mailbox, False, squire_edit_url=reverse("admin:committees_associationgroup_change", args=[assoc_group.id]),
                archive_addresses=settings.COMMITTEE_CONFIGS['archive_addresses']
            )
            infos.append(info)
        return infos

    def _init_unused_squire_addresses_list(self, aliases: List[MailcowAlias],
            member_aliases: List[AliasInfos], committee_aliases: List[AliasInfos],
            global_committee_aliases: List[AliasInfos]) -> List[AliasInfos]:
        """ TODO """
        # Only include aliases starting with [MANAGED BY SQUIRE]
        aliases = filter(lambda alias: alias.public_comment.startswith(self.mailcow_manager.SQUIRE_MANAGE_INDICATOR), aliases)
        # Ignore addresses that are member aliases
        aliases = filter(lambda alias: not any(1 for member_alias in member_aliases if member_alias.address == alias.address), aliases)
        # Ignore addresses that are committee aliases
        aliases = filter(lambda alias: not any(1 for comm_alias in committee_aliases if comm_alias.address == alias.address), aliases)
        # Ignore global committee aliases
        aliases = filter(lambda alias: not any(1 for comm_alias in global_committee_aliases if comm_alias.address == alias.address), aliases)

        return [
            AliasInfos(AliasStatus.ORPHAN.name, [{'name': addr, 'invalid': False} for addr in alias.goto],
                alias.address, alias_address_to_id(alias.address), alias.address, alias.private_comment, alias, False)
            for alias in aliases
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.mailcow_manager is None:
            return context

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
            context['member_aliases'] = self._init_member_alias_list(aliases, mailboxes)
            context['global_committee_aliases'] = self._init_global_committee_alias_list(aliases, mailboxes)
            context['committee_aliases'] = self._init_committee_alias_list(aliases, mailboxes)
            context['unused_aliases'] = self._init_unused_squire_addresses_list(aliases,
                context['member_aliases'], context['committee_aliases'], context['global_committee_aliases']
            )
        return context

    def post(self, request, *args, **kwargs):
        # One of the update buttons was pressed.
        if self.request.POST.get("alias_type", None) == "members":
            # Update all member aliases
            self.mailcow_manager.update_member_aliases()
            messages.success(self.request, "Member aliases updated.")
        elif self.request.POST.get("alias_type", None) == "global_committee":
            # Update all global committee aliases
            # TODO: self.mailcow_manager.update_member_aliases()
            messages.success(self.request, "Global committee aliases updated.")
        elif self.request.POST.get("alias_type", None) == "committees":
            # Update all committee aliases
            # TODO: Update user aliases
            self.mailcow_manager.update_committee_aliases()
            messages.success(self.request, "Committee aliases updated.")
        else:
            # Delete orphan data
            # TODO: self.mailcow_manager.update_member_aliases()
            messages.success(self.request, "Orphan data deleted.")

        return HttpResponseRedirect(self.request.get_full_path())
