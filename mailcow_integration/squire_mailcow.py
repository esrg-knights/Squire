from enum import Enum
import re
from typing import Dict, Optional, List

from django.apps import apps
from django.conf import settings
from django.template.loader import get_template

from mailcow_integration.api.client import MailcowAPIClient
from mailcow_integration.api.interface.alias import AliasType, MailcowAlias
from mailcow_integration.api.interface.rspamd import RspamdSettings

import logging
logger = logging.getLogger(__name__)

class SquireMailcowManager:
    """ TODO """
    INTERNAL_ALIAS_SETTING_NAME = "[MANAGED BY SQUIRE] Internal Alias"
    ALIAS_COMMITTEE_PUBLIC_COMMENT = "[MANAGED BY SQUIRE] Committee Alias"
    ALIAS_MEMBERS_PUBLIC_COMMENT = "[MANAGED BY SQUIRE] Members Alias"

    def __init__(self, mailcow_host: str, mailcow_api_key: str):
        self._client = MailcowAPIClient(mailcow_host, mailcow_api_key)

        # Cannot import directly because this file is imported before the app registry is set up
        self._model = apps.get_model("membership_file", "Member")

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
        """ Makes a list of aliases 'internal'. That is, these aliases can only
            be emailed from within one of the domains set up in Mailcow.
            See `internal_mailbox.conf` for the Rspamd configuration to achieve this.

            Example:
                `@example.com` is a domain set up in Mailcow.
                Using this function to make `members@example.com` interal ensures that
                `foo@spam.com` cannot send emails to `members@example.com` (those are
                discarded), while `importantperson@example.com` can send emails to
                `members@example.com`.
        """
        # Sort & escape addresses
        addresses = settings.INTERNAL_MEMBERS_ALIAS
        addresses = list(map(lambda addr: re.escape(addr), sorted(addresses)))

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
        return self._client.get_alias_all()

    def _get_alias_by_name(self, alias_address: str) -> MailcowAlias:
        """ TODO """
        aliases = self._client.get_alias_all()
        for alias in aliases:
            if alias.address == alias_address:
                return alias

    def _set_alias_by_name(self, alias_address: str, goto_addresses: List[str], public_comment: str, sogo_visible: bool) -> None:
        """ TODO """
        alias = self._get_alias_by_name(alias_address)

        # There is a race condition here when an alias is created in the Mailcow admin before Squire does so,
        #   but there is no way around that. The Mailcow API does not have a "create-if-not-exists" endpoint
        if alias is None:
            alias = MailcowAlias(alias_address, goto_addresses, active=True, public_comment=public_comment, sogo_visible=sogo_visible)
            self._client.create_alias(alias)
            return

        # Failsafe in case we attempt to overwrite an alias that is not managed by Squire.
        #   This should only happen if such an alias is modified in the Mailcow admin after its creation,
        #   as Squire _should_ prevent setting this alias in model fields otherwise.
        if alias.public_comment != public_comment:
            logging.error(f"Cannot update alias for {alias_address}. It already exists and is not managed by Squire! <{alias.public_comment}>")
            return

        alias.goto = goto_addresses
        alias.sogo_visible = sogo_visible
        res = self._client.update_alias(alias)
        print(res)
        print(res.content)

    def update_member_aliases(self) -> None:
        """ TODO """
        emails = self._model.objects.filter_active().values_list('email', flat=True)
        print(emails)
        self._set_alias_by_name(settings.INTERNAL_MEMBERS_ALIAS[0], emails, public_comment=self.ALIAS_MEMBERS_PUBLIC_COMMENT, sogo_visible=True)
