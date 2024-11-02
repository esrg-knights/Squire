from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import Dict, List, Optional, Tuple, TypedDict

from django.conf import settings
from django.db.models import QuerySet
from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.views.generic import TemplateView
from committees.models import AssociationGroup
from core.status_collective import AdminStatusViewMixin

from mailcow_integration.api.exceptions import (
    MailcowAPIAccessDenied,
    MailcowAPIReadWriteAccessDenied,
    MailcowAuthException,
    MailcowException,
)
from mailcow_integration.api.interface.alias import MailcowAlias
from mailcow_integration.api.interface.base import MailcowAPIResponse
from mailcow_integration.api.interface.mailbox import MailcowMailbox
from mailcow_integration.api.interface.rspamd import RspamdSettings
from mailcow_integration.dynamic_preferences_registry import alias_address_to_id
from mailcow_integration.squire_mailcow import AliasCategory, SquireMailcowManager, get_mailcow_manager

logger = logging.getLogger(__name__)


class AliasStatus(Enum):
    """Aliases that should exist according to Squire may not be in sync with those in Mailcow.
    This Enum indicates the disparity between the two.
    """

    VALID = 0  # Squire and mailcow are in sync
    MISSING = 1  # Alias is not in Mailcow, but should exist
    NOT_MANAGED_BY_SQUIRE = (
        2  # Alias is in Mailcow, but does not have a public comment indicating it is managed by Squire
    )
    OUTDATED = 3  # Alias goto-addresses do not match up with Squire
    RESERVED = 4  # Alias already reserved for a member-alias, but a committee has it as their contact info
    MAILBOX = 5  # Mailbox with the same name already exists; not managed by Squire
    ORPHAN = 6  # Alias is not needed by Squire, but existed in Mailcow


class SubscriberInfos(TypedDict):
    """Representation of a subscriber"""

    name: str
    invalid: bool


@dataclass
class AliasInfos:
    """Shared interface for email lists, regardless of whether it is for
    member aliases, committee aliases, or orphan data.
    """

    status: str  # One of AliasStatus.name
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


class MailcowStatusView(TemplateView):
    """An overview of aliases managed by Squire. Connects to the Mailcow API to determine whether
    such aliases are considered up-to-date. Also allows forced updates of each alias.
    """

    template_name = "mailcow_integration/admin_status/status.html"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.mailcow_manager: SquireMailcowManager = get_mailcow_manager()
        self._committee_addresses = AssociationGroup.objects.values_list("contact_email", flat=True)

    # TODO: A lot of this logic should be moved to SquireMailcowManager in case these kind of checks
    #   were to be used in forms and such. Right now, this is the only view that does something with this logic.
    def _get_alias_status(
        self,
        address: str,
        subscribers: QuerySet,
        alias_type: AliasCategory,
        aliases: List[MailcowAlias],
        mailboxes: List[MailcowMailbox],
        squire_comment: str,
    ) -> Tuple[AliasStatus, Optional[MailcowAlias], Optional[MailcowMailbox]]:
        """Gets the status for an address, along with the alias or mailbox data associated with that address (if any)."""
        if (
            alias_type != AliasCategory.MEMBER
            and address in settings.MEMBER_ALIASES
            or alias_type == AliasCategory.COMMITTEE
            and address in settings.COMMITTEE_CONFIGS["global_addresses"]
        ):
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
            elif alias.goto != (
                self.mailcow_manager.get_archive_adresses_for_type(alias_type, address)
                + self.mailcow_manager.clean_emails_flat(
                    subscribers,
                    email_field=("contact_email" if alias_type == AliasCategory.GLOBAL_COMMITTEE else "email"),
                    exclude=([] if alias_type == AliasCategory.GLOBAL_COMMITTEE else self._committee_addresses),
                )
            ):
                # Alias is outdated
                #   goto-addresses include archive addresses and subscriber's addresses
                #   goto-addresses exclude member-alias addresses and (usually) committee addresses
                return AliasStatus.OUTDATED, alias, None
            else:
                # Alias is valid
                return AliasStatus.VALID, alias, None
        else:
            # Alias does not exist
            return AliasStatus.MISSING, None, None

    def _get_alias_exposure_routes(
        self,
        address: str,
        aliases: List[MailcowAlias],
        mailboxes: List[MailcowMailbox],
        member_aliases: Dict[str, Dict],
    ) -> List[List[str]]:
        """Gets addresses through which an internal alias is exposed. That is, public addresses
        with the internal alias in their goto-addresses."""
        routes: List[List[str]] = []
        for alias in aliases:
            if address in alias.goto:
                # Address appears in the alias's goto
                if not next(
                    (
                        config["internal"]
                        for member_address, config in member_aliases.items()
                        if member_address == alias.address
                    ),
                    False,
                ):
                    # Exposed: The alias is a public (non-internal) member alias
                    routes.append([alias.address])
                else:
                    # The alias is an internal member alias, but it _might_ be exposed.
                    for route in self._get_alias_exposure_routes(alias.address, aliases, mailboxes, member_aliases):
                        route.append(alias.address)
                        routes.append(route)
        # Sort routes alphabetically
        return sorted(routes, key=lambda route: route[0])

    def _get_subscriberinfos_by_status(
        self,
        status: AliasStatus,
        subscribers: QuerySet,
        alias: Optional[MailcowAlias],
        alias_type: AliasCategory = AliasCategory.MEMBER,
    ) -> List[SubscriberInfos]:
        """Determines how subscribers should be displayed, based on the status of the alias"""
        if status == AliasStatus.NOT_MANAGED_BY_SQUIRE:
            # Not managed by Squire; no specific way to display subscribers
            return [{"name": addr, "invalid": False} for addr in alias.goto]
        elif status == AliasStatus.MAILBOX or status == AliasStatus.RESERVED:
            # Mailboxes or reserved aliases have no subscribers
            return []
        else:
            email_field = "email"
            get_name = lambda sub: sub.get_full_name()
            blocklist = []
            blocklist += self.mailcow_manager.BLOCKLISTED_EMAIL_ADDRESSES
            if alias_type == AliasCategory.GLOBAL_COMMITTEE:
                email_field = "contact_email"
                get_name = lambda sub: f"{sub.name} ({sub.get_type_display()})"
            else:
                blocklist += self._committee_addresses

            return [
                {
                    "name": format_html("{} &mdash; {}", get_name(sub), getattr(sub, email_field)),
                    "invalid": getattr(sub, email_field) in blocklist,
                }
                for sub in subscribers
            ]

    def _init_member_alias_list(
        self, aliases: List[MailcowAlias], mailboxes: List[MailcowMailbox]
    ) -> List[AliasInfos]:
        """Initialize member aliases. e.g. leden@example.com"""
        active_members = self.mailcow_manager.get_active_members()
        infos: List[AliasInfos] = []

        for address, config in settings.MEMBER_ALIASES.items():
            subscribers = self.mailcow_manager.get_subscribed_members(
                active_members, address, default=config["default_opt"]
            )
            status, alias, mailbox = self._get_alias_status(
                address,
                subscribers,
                AliasCategory.MEMBER,
                aliases,
                mailboxes,
                self.mailcow_manager.ALIAS_MEMBERS_PUBLIC_COMMENT,
            )

            exposure_routes = []
            if config["internal"]:
                if not self.mailcow_manager.is_address_internal(address):
                    exposure_routes.append([address, "Alias not located in Rspamd settings map."])
                exposure_routes += self._get_alias_exposure_routes(address, aliases, mailboxes, config)

            subscribers = self._get_subscriberinfos_by_status(status, subscribers, alias)
            info = AliasInfos(
                status.name,
                subscribers,
                address,
                "m_" + alias_address_to_id(address),
                config["title"],
                config["description"],
                alias or mailbox,
                config["internal"],
                exposure_routes,
                config["allow_opt_out"],
                archive_addresses=config["archive_addresses"],
            )
            infos.append(info)
        return infos

    def _init_global_committee_alias_list(
        self, aliases: List[MailcowAlias], mailboxes: List[MailcowMailbox]
    ) -> List[AliasInfos]:
        """Initialize global committee aliases. e.g. commissies@example.com"""
        infos: List[AliasInfos] = []
        subscribers = self.mailcow_manager.get_active_committees()

        for address in settings.COMMITTEE_CONFIGS["global_addresses"]:
            status, alias, mailbox = self._get_alias_status(
                address,
                subscribers,
                AliasCategory.GLOBAL_COMMITTEE,
                aliases,
                mailboxes,
                self.mailcow_manager.ALIAS_GLOBAL_COMMITTEE_PUBLIC_COMMENT,
            )

            exp_routes = []
            if not self.mailcow_manager.is_address_internal(address) and status != AliasStatus.RESERVED:
                exp_routes = [[address, "Alias not located in Rspamd settings map."]]

            info_subscribers = self._get_subscriberinfos_by_status(
                status, subscribers, alias, alias_type=AliasCategory.GLOBAL_COMMITTEE
            )
            info = AliasInfos(
                status.name,
                info_subscribers,
                address,
                "gc_" + alias_address_to_id(address),
                address,
                "Allows mailing all committees at the same time.",
                alias or mailbox,
                internal=True,
                exposure_routes=exp_routes,
                allow_opt_out=None,
                archive_addresses=settings.COMMITTEE_CONFIGS["global_archive_addresses"],
            )
            infos.append(info)
        return infos

    def _init_committee_alias_list(
        self, aliases: List[MailcowAlias], mailboxes: List[MailcowMailbox]
    ) -> List[AliasInfos]:
        """Initialize committee aliases. e.g. bg@example.com"""
        infos: List[AliasInfos] = []

        for assoc_group in self.mailcow_manager.get_active_committees():
            address = assoc_group.contact_email
            subscribers = assoc_group.members.order_by("email")

            status, alias, mailbox = self._get_alias_status(
                address,
                subscribers,
                AliasCategory.COMMITTEE,
                aliases,
                mailboxes,
                self.mailcow_manager.ALIAS_COMMITTEE_PUBLIC_COMMENT,
            )

            subscribers = self._get_subscriberinfos_by_status(status, subscribers, alias)
            info = AliasInfos(
                status.name,
                subscribers,
                address,
                "c_" + str(assoc_group.id),
                assoc_group.name,
                format_html(
                    "{} ({}): {}", assoc_group.name, assoc_group.get_type_display(), assoc_group.short_description
                ),
                alias or mailbox,
                False,
                squire_edit_url=reverse("admin:committees_associationgroup_change", args=[assoc_group.id]),
                archive_addresses=settings.COMMITTEE_CONFIGS["archive_addresses"],
            )
            infos.append(info)
        return infos

    def _init_unused_squire_addresses_list(
        self,
        aliases: List[MailcowAlias],
        member_aliases: List[AliasInfos],
        committee_aliases: List[AliasInfos],
        global_committee_aliases: List[AliasInfos],
    ) -> List[AliasInfos]:
        """Initialize orphan aliases. i.e. those no longer being used by Squire, but still present in Mailcow"""
        # Only include aliases starting with [MANAGED BY SQUIRE]
        aliases = filter(
            lambda alias: alias.public_comment.startswith(self.mailcow_manager.SQUIRE_MANAGE_INDICATOR), aliases
        )
        # Ignore addresses that are member aliases
        aliases = filter(
            lambda alias: not any(1 for member_alias in member_aliases if member_alias.address == alias.address),
            aliases,
        )
        # Ignore addresses that are committee aliases
        aliases = filter(
            lambda alias: not any(1 for comm_alias in committee_aliases if comm_alias.address == alias.address),
            aliases,
        )
        # Ignore global committee aliases
        aliases = filter(
            lambda alias: not any(1 for comm_alias in global_committee_aliases if comm_alias.address == alias.address),
            aliases,
        )

        return [
            AliasInfos(
                AliasStatus.ORPHAN.name,
                [{"name": addr, "invalid": False} for addr in alias.goto],
                alias.address,
                "o_" + alias_address_to_id(alias.address),
                alias.address,
                alias.private_comment,
                alias,
                False,
            )
            for alias in aliases
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.mailcow_manager is None:
            return context

        context["mailcow_host"] = self.mailcow_manager.mailcow_host
        try:
            aliases = list(self.mailcow_manager.get_alias_all(use_cache=False))
            mailboxes = list(self.mailcow_manager.get_mailbox_all(use_cache=False))
            # Force cache update; we don't care about the result
            self.mailcow_manager.get_internal_alias_rspamd_settings(use_cache=False)
        except MailcowAuthException as e:
            context["error"] = "No valid API key set."
        except MailcowAPIReadWriteAccessDenied as e:
            context["error"] = "API key only allows access to read operations, not write."
        except MailcowAPIAccessDenied as e:
            ip = str(e).rpartition(" ")[2]
            context["error"] = f"IP address is not whitelisted in the Mailcow admin: {ip}"
        except MailcowException as e:
            err = ", ".join(e.args)
            logger.error(err)
            context["error"] = err
        else:
            context["member_aliases"] = self._init_member_alias_list(aliases, mailboxes)
            context["global_committee_aliases"] = self._init_global_committee_alias_list(aliases, mailboxes)
            context["committee_aliases"] = self._init_committee_alias_list(aliases, mailboxes)
            context["unused_aliases"] = self._init_unused_squire_addresses_list(
                aliases, context["member_aliases"], context["committee_aliases"], context["global_committee_aliases"]
            )
            (
                context["internal_alias_rspamd_setting_allow"],
                context["internal_alias_rspamd_setting_block"],
            ) = self.mailcow_manager.get_internal_alias_rspamd_settings()
            context["mailcow_host"] = self.mailcow_manager.mailcow_host
        return context

    def post(self, request, *args, **kwargs):
        # One of the update buttons was pressed.
        errors: List[Tuple[str, MailcowException]] = []

        if request.POST.get("alias_type", None) == "members":
            # Update all member aliases
            errors = self.mailcow_manager.update_member_aliases()
            messages.success(self.request, "Member aliases updated.")
        elif request.POST.get("alias_type", None) == "global_committee":
            # Update all global committee aliases
            errors = self.mailcow_manager.update_global_committee_aliases()
            messages.success(self.request, "Global committee aliases updated.")
        elif request.POST.get("alias_type", None) == "committees":
            # Update all committee aliases
            errors = self.mailcow_manager.update_committee_aliases()
            messages.success(self.request, "Committee aliases updated.")
        elif request.POST.get("alias_type", None) == "orphan":
            # Delete orphan data
            unused_aliases: List[AliasInfos] = self.get_context_data()["unused_aliases"]
            unused_addresses = []
            for aliasinfo in unused_aliases:
                unused_addresses.append(aliasinfo.address)
            error = self.mailcow_manager.delete_aliases(unused_addresses, self.mailcow_manager.SQUIRE_MANAGE_INDICATOR)
            if error is None:
                messages.success(self.request, f"Orphan data deleted: {', '.join(unused_addresses)}.")
            else:
                messages.error(
                    self.request, f"Error deleting data: {', '.join(unused_addresses)}.\nException: {error}"
                )
        elif request.POST.get("alias_type", None) == "internal_alias":
            # Update Rspamd rule for internal aliases
            try:
                self.mailcow_manager.update_internal_addresses()
            except MailcowException as e:
                pass
        else:
            return HttpResponseBadRequest("Invalid alias_type passed")

        for addr, e in errors:
            messages.error(self.request, f"Error while updating alias: {addr}\nException: {e}")

        return HttpResponseRedirect(self.request.get_full_path())


class MailcowTabbedStatusView(AdminStatusViewMixin, MailcowStatusView):
    """Variant of the Mailcow status view to use in a tabbed ViewCollective"""
