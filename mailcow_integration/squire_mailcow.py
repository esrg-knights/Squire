import re
from typing import Optional, List

from django.apps import apps
from django.conf import settings
from django.db.models import Q, QuerySet
from django.template.loader import get_template

from mailcow_integration.api.client import MailcowAPIClient
from mailcow_integration.api.interface.alias import MailcowAlias
from mailcow_integration.api.interface.rspamd import RspamdSettings

import logging

logger = logging.getLogger(__name__)

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
    INTERNAL_ALIAS_SETTING_NAME = "[MANAGED BY SQUIRE] Internal Alias"
    ALIAS_COMMITTEE_PUBLIC_COMMENT = "[MANAGED BY SQUIRE] Committee Alias"
    ALIAS_MEMBERS_PUBLIC_COMMENT = "[MANAGED BY SQUIRE] Members Alias"

    def __init__(self, mailcow_host: str, mailcow_api_key: str):
        self._client = MailcowAPIClient(mailcow_host, mailcow_api_key)

        # Cannot import directly because this file is imported before the app registry is set up
        self._member_model = apps.get_model("membership_file", "Member")
        self._committee_model = apps.get_model("committees", "AssociationGroup")

        # List of internal addresses (sorted in order of appearance in the config)
        self._internal_aliases: List[str] = [
            alias_data['address'] for alias_data in settings.MEMBER_ALIASES.values() if alias_data['internal']
        ]

    def __str__(self) -> str:
        return f"SquireMailcowManager[{self._client.host}]"

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

    def get_all_aliases(self) -> List[MailcowAlias]:
        """ Gets all email aliases """
        return list(self._client.get_alias_all())

    def _get_alias_by_name(self, alias_address: str) -> Optional[MailcowAlias]:
        """ Gets the corresponding data of some alias address. E.g. foo@example.com """
        aliases = self._client.get_alias_all()
        for alias in aliases:
            if alias.address == alias_address:
                return alias

    def _set_alias_by_name(self, alias_address: str, goto_addresses: List[str], public_comment: str, sogo_visible: bool) -> None:
        """ Sets an alias's goto addresses, and optionally sets its visible in SOGo. If the corresponding
            Mailcow alias's public comment does not match `public_comment`, modifications are aborted.
            If the alias indicated by `alias_address` does not yet exist, it is created.
        """
        alias = self._get_alias_by_name(alias_address)
        # TODO: if updating multiple aliases, we don't need to do this every time

        # There is a race condition here when an alias is created in the Mailcow admin before Squire does so,
        #   but there is no way around that. The Mailcow API does not have a "create-if-not-exists" endpoint
        # TODO: Check mailboxes; this breaks if the alias is already a mailbox
        if alias is None:
            alias = MailcowAlias(alias_address, goto_addresses, active=True, public_comment=public_comment, sogo_visible=sogo_visible)
            self._client.create_alias(alias)
            return

        # Failsafe in case we attempt to overwrite an alias that is not managed by Squire.
        #   This should only happen if such an alias is modified in the Mailcow admin after its creation.
        if alias.public_comment != public_comment:
            logging.error(f"Cannot update alias for {alias_address}. It already exists and is not managed by Squire! <{alias.public_comment}>")
            return

        alias.goto = goto_addresses
        alias.sogo_visible = sogo_visible
        self._client.update_alias(alias)

    def get_active_members(self) -> QuerySet:
        """ Helper method to obtain a queryset of active members. That is, those that have active membership. """
        return self._member_model.objects.filter_active().order_by('email')

    def get_subscribed_members(self, active_members, alias_id: str, default: bool=True) -> QuerySet:
        """ Gets a Queryset of members subscribed to a specific member alias, based on their
            associated user's preferences. If users are opted-in by default for the given alias,
            then members without an associated user are included in this Queryset as well.
            If the default is opted-out, then such members are excluded.
        """
        # Member must have their preference set
        query = Q(
            user__userpreferencemodel__section="mail",
            user__userpreferencemodel__name=alias_id,
            # Convert value to string (dynamic preferences serializes everything to a string)
            user__userpreferencemodel__raw_value=str(True),
        )

        # If the default is opt-in, members that do not have a corresponding user should also be included
        if default:
            query |= Q(user__isnull=True)

        # Filter members
        return active_members.filter(query)

    def update_member_aliases(self) -> None:
        """ Updates all member aliases """
        # Fetch active members here so the results can be cached
        active_members = self.get_active_members()

        for alias_id, alias_data in settings.MEMBER_ALIASES.items():
            print(f"updating {alias_id} ({alias_data['address']})")
            emails = list(
                self.get_subscribed_members(active_members, alias_id, default=alias_data['default_opt'])\
                    .values_list('email', flat=True))
            print(emails)
            self._set_alias_by_name(alias_data['address'], emails, public_comment=self.ALIAS_MEMBERS_PUBLIC_COMMENT, sogo_visible=False)

    def update_committee_aliases(self) -> None:
        """ TODO
        """
        AssociationGroup = self._committee_model
        assoc_groups = AssociationGroup.objects.filter(
            type__in=[AssociationGroup.COMMITTEE, AssociationGroup.GUILD, AssociationGroup.WORKGROUP],
            contact_email__isnull=False
        ) # TODO: Remove this duplication

        for assoc_group in assoc_groups:
            emails = list(assoc_group.members.filter_active().order_by('email').values_list('email', flat=True))
            print(assoc_group)
            print(emails)

            self._set_alias_by_name(assoc_group.contact_email, emails, public_comment=self.ALIAS_COMMITTEE_PUBLIC_COMMENT, sogo_visible=False)


