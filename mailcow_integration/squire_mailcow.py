from enum import Enum
import re
from typing import Dict, Optional, List, Tuple

from django.apps import apps
from django.conf import settings
from django.db.models import QuerySet, Exists, OuterRef
from django.template.loader import get_template

from mailcow_integration.api.client import MailcowAPIClient
from mailcow_integration.api.exceptions import MailcowException
from mailcow_integration.api.interface.alias import MailcowAlias
from mailcow_integration.api.interface.mailbox import MailcowMailbox
from mailcow_integration.api.interface.rspamd import RspamdSettings
from mailcow_integration.dynamic_preferences_registry import alias_address_to_id

import logging


logger = logging.getLogger(__name__)


def get_mailcow_manager() -> Optional["SquireMailcowManager"]:
    """Access the AppConfig to obtain Squire's Mailcow Manager that connects to the Mailcow API."""
    return apps.get_app_config("mailcow_integration").mailcow_client


class AliasCategory(Enum):
    """Squire's Mailcow Aliases can exist in different forms.
    1. Member aliases are used to email all Squire Members active in the current year.
    2. Global committee aliases are used to email all committees (Committees and orders)
        registered in Squire.
    3. Committee aliases are used to email a specific committee (or order).
    """

    MEMBER = 0  # Addresses for emailing all* members
    GLOBAL_COMMITTEE = 1  # Addresses for emailing all* committees
    COMMITTEE = 2  # Addresses for emailing specific committees and its members


class SquireMailcowManager:
    """All interactions Squire makes with the Mailcow API are handled through this class.
    It is responsible for adding members' emails to a group of member aliases (depending
    on their stored preferences), and adding members' emails to the aliases of committees
    they are in.

    When this class interacts with the Mailcow API, it leaves behind some form of
    "MANAGED BY SQUIRE" comment. If this class sees an already existing item in the API it
    wishes to modify, it will only do so if this comment is present. This prevents it from
    accidentally overwriting information that a Mailcow admin may have added. Furthermore,
    it also allows manual overrides by Mailcow admins.
    """

    SQUIRE_MANAGE_INDICATOR = "[MANAGED BY SQUIRE]" if not settings.DEBUG else "[DEV][MANAGED BY SQUIRE]"
    INTERNAL_ALIAS_SETTING_NAME = SQUIRE_MANAGE_INDICATOR + " Internal Alias (%s)"
    INTERNAL_ALIAS_SETTING_WHITELIST_NAME = "Authenticated"
    INTERNAL_ALIAS_SETTING_BLACKLIST_NAME = "Reject"
    ALIAS_COMMITTEE_PUBLIC_COMMENT = f"{SQUIRE_MANAGE_INDICATOR} Committee Alias"
    ALIAS_MEMBERS_PUBLIC_COMMENT = f"{SQUIRE_MANAGE_INDICATOR} Members Alias"
    ALIAS_GLOBAL_COMMITTEE_PUBLIC_COMMENT = f"{SQUIRE_MANAGE_INDICATOR} Global Committee Alias"

    def __init__(self, mailcow_host: str, mailcow_api_key: str):
        self._client = MailcowAPIClient(mailcow_host, mailcow_api_key)

        # Cannot import directly because this class is initialized before the app registry is set up
        self._member_model = apps.get_model("membership_file", "Member")
        self._committee_model = apps.get_model("committees", "AssociationGroup")
        self._user_preferences_model = apps.get_model("dynamic_preferences_users", "UserPreferenceModel")

        # List of internal addresses (sorted in order of appearance in the config)
        self.INTERNAL_ALIAS_ADDRESSES: List[str] = [
            address for address, alias_data in settings.MEMBER_ALIASES.items() if alias_data["internal"]
        ] + settings.COMMITTEE_CONFIGS["global_addresses"]

        # List of all member alias addresses; these should never be included in an alias's goto addresses
        self.BLOCKLISTED_EMAIL_ADDRESSES: List[str] = [
            address for address in settings.MEMBER_ALIASES.keys()
        ] + settings.COMMITTEE_CONFIGS["global_addresses"]

        # Caches
        self._internal_rspamd_setting_whitelist: Optional[RspamdSettings] = None
        self._internal_rspamd_setting_blacklist: Optional[RspamdSettings] = None
        self._alias_cache: Optional[List[MailcowAlias]] = None
        self._mailbox_cache: Optional[List[MailcowMailbox]] = None
        self._alias_map_cache: Optional[Dict[str, MailcowAlias]] = None
        self._mailbox_map_cache: Optional[Dict[str, MailcowMailbox]] = None

    @property
    def mailcow_host(self):
        return self._client.host

    def __str__(self) -> str:
        return f"SquireMailcowManager[{self.mailcow_host}]"

    def clean_emails(self, queryset: QuerySet, email_field="email", exclude: Optional[List[str]] = None) -> QuerySet:
        """Cleans a queryset of models with an email field (of any name),
        by removing blocklisted email addresses.
        Additional blocklisted addresses can be passed through the
        `extra` keyword argument.
        """
        blocklisted_addresses = []  # NOTE: Do not perform arithmetic on BLOCKLIST directly to prevent modification
        blocklisted_addresses += self.BLOCKLISTED_EMAIL_ADDRESSES
        if exclude is not None:
            blocklisted_addresses += exclude
        queryset = queryset.exclude(**{f"{email_field}__in": blocklisted_addresses}).order_by(email_field)
        return queryset

    def clean_emails_flat(self, queryset: QuerySet, email_field="email", **kwargs) -> List[str]:
        """Does the same as `clean_emails`, but also flattens the resulting queryset"""
        queryset = self.clean_emails(queryset, email_field, **kwargs)
        return list(queryset.values_list(email_field, flat=True))

    def get_internal_alias_rspamd_settings(
        self, use_cache=True
    ) -> Tuple[Optional[RspamdSettings], Optional[RspamdSettings]]:
        """Gets the Rspamd settings (if it exists) that disallows external domains
        to send emails to a specific set of email addresses. Squire recognises
        which Rspamd setting to find based on the setting's name.
        See `self.INTERNAL_ALIAS_SETTING_NAME`
        """
        if (
            self._internal_rspamd_setting_whitelist is not None
            and self._internal_rspamd_setting_blacklist is not None
            and use_cache
        ):
            return self._internal_rspamd_setting_whitelist, self._internal_rspamd_setting_blacklist

        self._internal_rspamd_setting_whitelist = None
        self._internal_rspamd_setting_blacklist = None

        # Fetch all Rspamd settings
        settings = self._client.get_rspamd_setting_all()
        for setting in settings:
            if setting is None:
                continue
            # Setting description matches the one we normally set
            if setting.desc == self.INTERNAL_ALIAS_SETTING_NAME % self.INTERNAL_ALIAS_SETTING_WHITELIST_NAME:
                self._internal_rspamd_setting_whitelist = setting
            elif setting.desc == self.INTERNAL_ALIAS_SETTING_NAME % self.INTERNAL_ALIAS_SETTING_BLACKLIST_NAME:
                self._internal_rspamd_setting_blacklist = setting
        return (self._internal_rspamd_setting_whitelist, self._internal_rspamd_setting_blacklist)

    def is_address_internal(self, address: str) -> bool:
        """Whether an alias address is made internal by means of an Rspamd setting"""
        setting_w, setting_b = self.get_internal_alias_rspamd_settings()
        if setting_w is None or not setting_w.active or setting_b is None or not setting_b.active:
            return False

        prefix = re.escape('rcpt = "/^(')
        suffix = re.escape(')$/"')
        wildcard = '[^"\n]*'
        # Double escape since we're using regex to find a match ourselves
        address = re.escape(re.escape(address))
        mtch_w = re.search(f"{prefix}{wildcard}{address}{wildcard}{suffix}", setting_w.content)
        mtch_b = re.search(f"{prefix}{wildcard}{address}{wildcard}{suffix}", setting_b.content)
        return mtch_w is not None and mtch_b is not None

    def update_internal_alias_setting(self, addresses: List[str], setting: RspamdSettings, is_whitelist_setting: bool):
        """Updates the allow/block setting"""
        if setting is not None and setting.active and f'rcpt = "/^({"|".join(addresses)})$/"' in setting.content:
            # Setting already exists, is active, and is up-to-date; no need to do anything
            return

        # Setting emails are different than from what we expect, or the setting
        #   does not yet exist
        subtemplate_name = "allow" if is_whitelist_setting else "block"
        subsetting_name = (
            self.INTERNAL_ALIAS_SETTING_WHITELIST_NAME
            if is_whitelist_setting
            else self.INTERNAL_ALIAS_SETTING_BLACKLIST_NAME
        )

        template = get_template("mailcow_integration/internal_mailbox_%s.conf" % subtemplate_name)
        setting_content = template.render({"addresses": addresses})
        id = setting.id if setting is not None else None
        setting = RspamdSettings(id, self.INTERNAL_ALIAS_SETTING_NAME % subsetting_name, setting_content, True)

        if setting.id is None:
            # Setting does not yet exist
            self._client.create_rspamd_setting(setting)
        else:
            # Setting exists but should be updated
            self._client.update_rspamd_setting(setting)

    def update_internal_addresses(self) -> None:
        """Makes specific member aliases 'internal'. That is, these aliases can only
        be emailed from within one of the domains set up in Mailcow.
        See `templates/internal_mailbox_<allow/block>.conf` for the Rspamd configuration used to
        achieve this.

        Example:
            `@example.com` is a domain set up in Mailcow
            members@example.com is an internal member address according to Squire's mailcowconfig.json
            Using this function ensures that `foo@spam.com` (note the domain) cannot send emails to
            `members@example.com` (those are rejected), while `importantperson@example.com` (note the domain)
            can send emails to `members@example.com`.
            Spoofed sender addresses are properly discarded as well.
        """
        # Escape addresses
        addresses = self.INTERNAL_ALIAS_ADDRESSES
        addresses = list(map(lambda addr: re.escape(addr), addresses))

        setting_w, setting_b = self.get_internal_alias_rspamd_settings(use_cache=False)
        self.update_internal_alias_setting(addresses, setting_w, True)
        self.update_internal_alias_setting(addresses, setting_b, False)

    def get_alias_all(self, use_cache=True) -> List[MailcowAlias]:
        """Gets all email aliases"""
        if use_cache and self._alias_cache is not None:
            return self._alias_cache
        self._alias_cache = [a for a in self._client.get_alias_all() if a is not None]
        self._alias_map_cache = None
        return self._alias_cache

    def get_mailbox_all(self, use_cache=True) -> List[MailcowMailbox]:
        """Gets all mailboxes"""
        if use_cache and self._mailbox_cache is not None:
            return self._mailbox_cache
        self._mailbox_cache = [m for m in self._client.get_mailbox_all() if m is not None]
        self._mailbox_map_cache = None
        return self._mailbox_cache

    @property
    def alias_map(self) -> Dict[str, MailcowAlias]:
        """A mapping from alias addresses to a MailcowAlias"""
        if self._alias_map_cache is not None and self._alias_cache is not None:
            return self._alias_map_cache
        aliases = self.get_alias_all()
        self._alias_map_cache = {alias.address: alias for alias in aliases}
        return self._alias_map_cache

    @property
    def mailbox_map(self) -> Dict[str, MailcowMailbox]:
        """A mapping from mailbox addresses to a MailcowMailbox"""
        if self._mailbox_map_cache is not None and self._mailbox_cache is not None:
            return self._mailbox_map_cache
        mailboxes = self.get_mailbox_all()
        self._mailbox_map_cache = {mailbox.username: mailbox for mailbox in mailboxes}
        return self._mailbox_map_cache

    def delete_aliases(
        self, alias_addresses: List[str], public_comment: Optional[str] = None
    ) -> Optional[MailcowException]:
        """Deletes a given list of aliases. Returns the error returned by the Mailcow API (if any)"""
        public_comment = public_comment or self.ALIAS_COMMITTEE_PUBLIC_COMMENT
        aliases: List[MailcowAlias] = []

        try:
            for address in alias_addresses:
                alias = self.alias_map.get(address, None)
                if alias is not None and alias.public_comment.startswith(public_comment):
                    aliases.append(alias)

            if aliases:
                # Delete aliases themselves
                self._client.delete_aliases(aliases)

                # Invalidate cache
                self._alias_cache = None
        except MailcowException as e:
            return e

    def _set_alias_by_name(self, address: str, goto_addresses: List[str], public_comment: str) -> None:
        """Sets an alias's goto addresses, and optionally sets its visible in SOGo. If the corresponding
        Mailcow alias's public comment does not match `public_comment`, modifications are aborted.
        If the alias indicated by `alias_address` does not yet exist, it is created.
        `alias_map` and `mailbox_map` are mappings of existing email aliases and mailboxes.
        """
        assert address not in self.mailbox_map

        alias = self.alias_map.get(address, None)

        # There is a race condition here when an alias is created in the Mailcow admin before Squire does so,
        #   but there is no way around that. The Mailcow API does not have a "create-if-not-exists" endpoint
        if alias is None:
            alias = MailcowAlias(
                address, goto_addresses, active=True, public_comment=public_comment, sogo_visible=False
            )
            self._client.create_alias(alias)
            return

        # Failsafe in case we attempt to overwrite an alias that is not managed by Squire.
        #   This should only happen if such an alias is modified in the Mailcow admin after its creation.
        if alias.public_comment != public_comment:
            logger.warning(
                f"Cannot update alias for {address}. It already exists and is not managed by Squire! <{alias.public_comment}>"
            )
            return

        alias.active = True
        if not goto_addresses:
            # If the alias is emtpy, Mailcow will accept the response and act as if things were properly changed.
            #   In practise, all changes are ignored!
            # As a failsafe, this just disables the alias.
            alias.active = False
        else:
            alias.goto = goto_addresses
        alias.sogo_visible = False
        self._client.update_alias(alias)

    def get_active_members(self) -> QuerySet:
        """Helper method to obtain a queryset of active members. That is, those that have active membership."""
        return self._member_model.objects.filter_active()

    def get_subscribed_members(self, active_members: QuerySet, alias_address: str, default: bool = True) -> QuerySet:
        """Gets a Queryset of members subscribed to a specific member alias, based on their
        associated user's preferences. If users are opted-in by default for the given alias,
        then members without an explicit preference are included in this Queryset as well.
        If the default is opted-out, then such members are excluded.
        """
        alias_id = alias_address_to_id(alias_address)

        # Find members who have a specific opt-in/opt-out status
        #   If the default is opt-out, only keep those with an explicit opt-out preference
        opts = Exists(
            self._user_preferences_model.objects.filter(
                instance_id=OuterRef("user_id"),
                section="mail",
                name=alias_id,
                raw_value=str(not default),  # dynamic preferences stores everything as a string
            )
        )

        if default:
            # If the default is opt-in, exclude users that have not
            #   explicitly opted-out. Keep those without explicit preferences.
            opts = ~opts

        return active_members.filter(opts)

    def get_archive_adresses_for_type(self, alias_type: AliasCategory, address: str) -> List[str]:
        """Gets a list of email addresses that are used as an archive for an alias-address"""
        if alias_type == AliasCategory.MEMBER:
            return settings.MEMBER_ALIASES[address]["archive_addresses"]
        elif alias_type == AliasCategory.GLOBAL_COMMITTEE:
            return settings.COMMITTEE_CONFIGS["global_archive_addresses"]
        return settings.COMMITTEE_CONFIGS["archive_addresses"]

    def update_member_aliases(self) -> List[Tuple[str, MailcowException]]:
        """Updates all member aliases. Returns a list of addresses for which the API returned an error"""
        # Fetch active members here so the results can be cached
        errors = []
        active_members = self.get_active_members()
        committee_emails = self._committee_model.objects.values_list("contact_email", flat=True)

        for alias_address, alias_data in settings.MEMBER_ALIASES.items():
            try:
                if alias_address in self.mailbox_map:
                    logger.warning(f"Skipping over {alias_address}: Mailbox with the same name already exists")
                    continue

                logger.info(f"Forced updating {alias_address}")
                emails = self.clean_emails_flat(
                    self.get_subscribed_members(active_members, alias_address, default=alias_data["default_opt"]),
                    exclude=committee_emails,
                )
                emails = self.get_archive_adresses_for_type(AliasCategory.MEMBER, alias_address) + emails
                self._set_alias_by_name(alias_address, emails, public_comment=self.ALIAS_MEMBERS_PUBLIC_COMMENT)
            except MailcowException as e:
                errors.append((alias_address, e))
        self._alias_cache = None
        return errors

    def get_active_committees(self):
        """Gets a queryset containing all associationGroups that should have an alias setup"""
        AssociationGroup = self._committee_model
        return AssociationGroup.objects.filter(
            type__in=[AssociationGroup.COMMITTEE, AssociationGroup.ORDER, AssociationGroup.WORKGROUP],
            contact_email__isnull=False,
        )

    def update_committee_aliases(
        self, limit_update_to: Optional[List[str]] = None
    ) -> List[Tuple[str, MailcowException]]:
        """Updates all committee aliases, or a subset thereof. Returns a list of addresses for which the API returned an error"""
        errors = []
        committee_emails = self._committee_model.objects.values_list("contact_email", flat=True)
        valid_groups = self.clean_emails(self.get_active_committees(), email_field="contact_email")
        if limit_update_to is not None:
            # Only update a selection of committee aliases
            valid_groups = valid_groups.filter(contact_email__in=limit_update_to)

        for assoc_group in valid_groups:
            try:
                if assoc_group.contact_email in self.mailbox_map:
                    logger.warning(
                        f"Skipping over {assoc_group} ({assoc_group.contact_email}): Mailbox with the same name already exists"
                    )
                    continue
                # NOTE: Include all committee member emails here, not just active members' ones
                goto_emails = self.clean_emails_flat(assoc_group.members, exclude=committee_emails)
                logger.info(f"Forced updating {assoc_group} ({len(goto_emails)} subscribers)")
                goto_emails = (
                    self.get_archive_adresses_for_type(AliasCategory.COMMITTEE, assoc_group.contact_email)
                    + goto_emails
                )

                self._set_alias_by_name(
                    assoc_group.contact_email, goto_emails, public_comment=self.ALIAS_COMMITTEE_PUBLIC_COMMENT
                )
            except MailcowException as e:
                errors.append((assoc_group.contact_email, e))
        self._alias_cache = None
        return errors

    def update_global_committee_aliases(self) -> List[Tuple[str, MailcowException]]:
        """Updates all global committee aliases Returns a list of addresses for which the API returned an error"""
        errors = []
        for alias_address in filter(
            lambda address: address not in settings.MEMBER_ALIASES.keys(),
            settings.COMMITTEE_CONFIGS["global_addresses"],
        ):
            try:
                if alias_address in self.mailbox_map:
                    logger.warning(f"Skipping over {alias_address}: Mailbox with the same name already exists")
                    continue

                logger.info(f"Forced updating {alias_address}")
                emails = self.clean_emails_flat(self.get_active_committees(), email_field="contact_email")
                emails = self.get_archive_adresses_for_type(AliasCategory.GLOBAL_COMMITTEE, alias_address) + emails

                self._set_alias_by_name(
                    alias_address, emails, public_comment=self.ALIAS_GLOBAL_COMMITTEE_PUBLIC_COMMENT
                )
            except MailcowException as e:
                errors.append((alias_address, e))
        self._alias_cache = None
        return errors
