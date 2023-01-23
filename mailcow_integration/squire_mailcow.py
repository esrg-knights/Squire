from enum import Enum
import re
from typing import Dict, Optional, List

from django.apps import apps
from django.conf import settings
from django.db.models import Q, QuerySet, Exists, OuterRef
from django.template.loader import get_template

from mailcow_integration.api.client import MailcowAPIClient
from mailcow_integration.api.interface.alias import MailcowAlias
from mailcow_integration.api.interface.mailbox import MailcowMailbox
from mailcow_integration.api.interface.rspamd import RspamdSettings
from mailcow_integration.dynamic_preferences_registry import alias_address_to_id

import logging


logger = logging.getLogger(__name__)

def get_mailcow_manager() -> Optional['SquireMailcowManager']:
    """ Access the AppConfig to obtain Squire's Mailcow Manager that connects to the Mailcow API. """
    return apps.get_app_config("mailcow_integration").mailcow_client

class AliasCategory(Enum):
    """ TODO """
    MEMBER = 0 # Addresses for emailing all* members
    GLOBAL_COMMITTEE = 1 # Addresses for emailing all* committees
    COMMITTEE = 2 # Addresses for emailing specific committees and its members

class SquireMailcowManager:
    """ All interactions Squire makes with the Mailcow API are handled through this class.
        It is responsible for adding members' emails to a group of member aliases (depending
        on their stored preferences), and adding members' emails to the aliases of committees
        they are in.

        When this class interacts with the Mailcow API, it leaves behind some form of
        "MANAGED BY SQUIRE" comment. If this class sees an already existing item in the API it
        wishes to modify, it will only do so if this comment is present. This prevents it from
        accidentally overwriting information that a Mailcow admin may have added. Furthermore,
        it also allows manual overrides by Mailcow admins.
    """
    SQUIRE_MANAGE_INDICATOR = "[MANAGED BY SQUIRE]"
    INTERNAL_ALIAS_SETTING_NAME = SQUIRE_MANAGE_INDICATOR + " Internal Alias"
    ALIAS_COMMITTEE_PUBLIC_COMMENT = SQUIRE_MANAGE_INDICATOR + " Committee Alias"
    ALIAS_MEMBERS_PUBLIC_COMMENT = SQUIRE_MANAGE_INDICATOR + " Members Alias"
    ALIAS_GLOBAL_COMMITTEE_PUBLIC_COMMENT = SQUIRE_MANAGE_INDICATOR + " Global Committee Alias"

    def __init__(self, mailcow_host: str, mailcow_api_key: str):
        self._client = MailcowAPIClient(mailcow_host, mailcow_api_key)

        # Cannot import directly because this file is imported before the app registry is set up
        self._member_model = apps.get_model("membership_file", "Member")
        self._committee_model = apps.get_model("committees", "AssociationGroup")
        self._user_preferences_model = apps.get_model("dynamic_preferences_users", "UserPreferenceModel")

        # List of internal addresses (sorted in order of appearance in the config)
        self._internal_aliases: List[str] = [
            address for address, alias_data in settings.MEMBER_ALIASES.items() if alias_data['internal']
        ]

        # List of all member alias addresses; these should never be included in an alias's goto addresses
        self._member_alias_addresses: List[str] = [
            address for address, alias_data in settings.MEMBER_ALIASES.items()
        ]

    @property
    def mailcow_host(self):
        return self._client.host

    def __str__(self) -> str:
        return f"SquireMailcowManager[{self._client.host}]"

    def clean_alias_emails(self, queryset, email_field="email", flatten=True) -> List[str]:
        """ TODO """
        queryset = queryset.exclude(**{f"{email_field}__in": self._member_alias_addresses}).order_by(email_field)
        if flatten:
            return list(queryset.values_list(email_field, flat=True))
        return queryset

    def _get_rspamd_internal_alias_setting(self) -> Optional[RspamdSettings]:
        """ Gets the Rspamd setting (if it exists) that is used by Squire
            to mark email aliases as 'internal'. Squire recognises which
            Rspamd setting to use based on the setting's name
            (`self.INTERNAL_ALIAS_SETTING_NAME`).
        """
        # Fetch all Rspamd settings
        settings = self._client.get_rspamd_setting_all()
        for setting in settings:
            # Setting description matches the one we normally set
            if setting.desc == self.INTERNAL_ALIAS_SETTING_NAME:
                return setting
        return None

    # TODO: What happens if I set one of the internal-addresses as my own address, and then email a committee's address that "my address" is also
    def set_internal_addresses(self) -> None:
        """ Makes a list of member aliases 'internal'. That is, these aliases can only
            be emailed from within one of the domains set up in Mailcow.
            See `internal_mailbox.conf` for the Rspamd configuration used to achieve this.

            Example:
                `@example.com` is a domain set up in Mailcow.
                Using this function to make `members@example.com` interal ensures that
                `foo@spam.com` cannot send emails to `members@example.com` (those are
                discarded), while `importantperson@example.com` can send emails to
                `members@example.com`. Spoofed sender addresses are properly discarded
                as well.
        """
        # Escape addresses
        addresses = self._internal_aliases
        addresses = list(map(lambda addr: re.escape(addr), addresses))

        # Fetch existing rspamd settings
        setting = self._get_rspamd_internal_alias_setting()
        if setting is not None and setting.active and f'rcpt = "/^({"|".join(addresses)})$/"' in setting.content:
            # Setting already exists and is active; no need to do anything
            return

        # Setting emails are different than from what we expect, or the setting
        #   does not yet exist
        template = get_template('mailcow_integration/internal_mailbox.conf')
        setting_content = template.render({
            'addresses': addresses
        })
        id = setting.id if setting is not None else None
        setting = RspamdSettings(id, self.INTERNAL_ALIAS_SETTING_NAME, setting_content, True)

        if setting.id is None:
            # Setting does not yet exist
            self._client.create_rspamd_setting(setting)
        else:
            # Setting exists but should be updated
            setting.content = setting_content
            self._client.update_rspamd_setting(setting)

    def get_alias_all(self, use_cache=True) -> List[MailcowAlias]:
        """ Gets all email aliases """
        return list(self._client.get_alias_all(use_cache=use_cache))

    def get_mailbox_all(self, use_cache=True) -> List[MailcowMailbox]:
        """ Gets all mailboxes """
        return list(self._client.get_mailbox_all(use_cache=use_cache))

    def _map_alias_by_name(self) -> Dict[str, MailcowAlias]:
        """ TODO """
        aliases = self._client.get_alias_all()
        return { alias.address: alias for alias in aliases }

    def _map_mailbox_by_name(self) -> Dict[str, MailcowMailbox]:
        mailboxes = self._client.get_mailbox_all()
        return { mailbox.username: mailbox for mailbox in mailboxes}

    # def _get_alias_by_name(self, alias_address: str) -> Optional[MailcowAlias]:
    #     """ Gets the corresponding data of some alias address. E.g. foo@example.com """
    #     aliases = self._client.get_alias_all()
    #     for alias in aliases:
    #         if alias.address == alias_address:
    #             return alias


    def _set_alias_by_name(self, alias_address: str, goto_addresses: List[str], public_comment: str,
            alias_map: Dict[str, MailcowAlias], mailbox_map: Dict[str, MailcowMailbox]) -> None:
        """ Sets an alias's goto addresses, and optionally sets its visible in SOGo. If the corresponding
            Mailcow alias's public comment does not match `public_comment`, modifications are aborted.
            If the alias indicated by `alias_address` does not yet exist, it is created.
            `alias_map` and `mailbox_map` are mappings of existing email aliases and mailboxes.
        """
        alias = alias_map.get(alias_address, None)

        # There is a race condition here when an alias is created in the Mailcow admin before Squire does so,
        #   but there is no way around that. The Mailcow API does not have a "create-if-not-exists" endpoint
        # TODO: Check mailboxes; this breaks if the alias is already a mailbox
        if alias is None:
            alias = MailcowAlias(alias_address, goto_addresses, active=True, public_comment=public_comment, sogo_visible=False)
            self._client.create_alias(alias)
            return

        # Failsafe in case we attempt to overwrite an alias that is not managed by Squire.
        #   This should only happen if such an alias is modified in the Mailcow admin after its creation.
        if alias.public_comment != public_comment:
            logging.error(f"Cannot update alias for {alias_address}. It already exists and is not managed by Squire! <{alias.public_comment}>")
            return

        if not alias.goto:
            # If the alias is emtpy, Mailcow will accept the response and act as if things were properly changed.
            #   In practise, all changes are ignored!
            # TODO:
            pass

        alias.goto = goto_addresses
        alias.sogo_visible = False
        self._client.update_alias(alias)

    def get_active_members(self) -> QuerySet:
        """ Helper method to obtain a queryset of active members. That is, those that have active membership. """
        return self._member_model.objects.filter_active()

    def get_subscribed_members(self, active_members: QuerySet, alias_address: str, default: bool=True) -> QuerySet:
        """ Gets a Queryset of members subscribed to a specific member alias, based on their
            associated user's preferences. If users are opted-in by default for the given alias,
            then members without an explicit preference are included in this Queryset as well.
            If the default is opted-out, then such members are excluded.
        """
        alias_id = alias_address_to_id(alias_address)

        # Find members who have a specific opt-in/opt-out status
        #   If the default is opt-out, only keep those with an explicit opt-out preference
        opts = Exists(self._user_preferences_model.objects.filter(
            instance_id=OuterRef('user_id'),
            section="mail",
            name=alias_id,
            raw_value=str(not default) # dynamic preferences stores everything as a string
        ))

        if default:
            # If the default is opt-in, exclude users that have not
            #   explicitly opted-out. Keep those without explicit preferences.
            opts = ~opts

        return active_members.filter(opts)

    def get_archive_adresses_for_type(self, alias_type: AliasCategory, address: str) -> List[str]:
        """ TODO """
        if alias_type == AliasCategory.MEMBER:
            return settings.MEMBER_ALIASES[address]["archive_addresses"]
        elif alias_type == AliasCategory.GLOBAL_COMMITTEE:
            return settings.COMMITTEE_CONFIGS["global_archive_addresses"]
        return settings.COMMITTEE_CONFIGS["archive_addresses"]

    def update_member_aliases(self) -> None:
        """ Updates all member aliases """
        # Fetch active members here so the results can be cached
        active_members = self.get_active_members()
        existing_aliases = self._map_alias_by_name()
        existing_mailboxes = self._map_mailbox_by_name()

        for alias_id, alias_data in settings.MEMBER_ALIASES.items():
            if alias_data['address'] in existing_mailboxes:
                logger.warning(f"Skipping over {alias_id} ({alias_data['address']}): Mailbox with the same name already exists")
                continue

            logger.info(f"Forced updating {alias_id} ({alias_data['address']})")
            emails = self.clean_alias_emails(
                self.get_subscribed_members(active_members, alias_id, default=alias_data['default_opt'])
            )
            # emails.append(settings.MEMBER_ALIAS_ARCHIVE_ADDRESS)
            logger.info(emails)

            self._set_alias_by_name(alias_data['address'], emails, public_comment=self.ALIAS_MEMBERS_PUBLIC_COMMENT,
                alias_map=existing_aliases, mailbox_map=existing_mailboxes)

    def get_alias_committees(self):
        """ Gets a queryset containing all associationGroups that should have an alias setup """
        AssociationGroup = self._committee_model
        return AssociationGroup.objects.filter(
            type__in=[AssociationGroup.COMMITTEE, AssociationGroup.GUILD, AssociationGroup.WORKGROUP],
            contact_email__isnull=False
        )

    def update_committee_aliases(self) -> None:
        """ TODO
        """
        existing_aliases = self._map_alias_by_name()
        existing_mailboxes = self._map_mailbox_by_name()

        for assoc_group in self.clean_alias_emails(self.get_alias_committees(), email_field="contact_email", flatten=False):
            if assoc_group.contact_email in existing_mailboxes:
                logger.warning(f"Skipping over {assoc_group} ({assoc_group.contact_email}): Mailbox with the same name already exists")
                continue

            emails = self.clean_alias_emails(assoc_group.members.filter_active())
            # emails.append(settings.COMMITTEE_ALIAS_ARCHIVE_ADDRESS)
            logger.info(f"Forced updating {assoc_group} ({len(emails)} subscribers)")

            self._set_alias_by_name(assoc_group.contact_email, emails, public_comment=self.ALIAS_COMMITTEE_PUBLIC_COMMENT,
                alias_map=existing_aliases, mailbox_map=existing_mailboxes)
