import re
from typing import Optional

from django.template.loader import get_template

from mailcow_integration.api.client import MailcowAPIClient
from mailcow_integration.api.interface.rspamd import RspamdSettings


class SquireMailcowManager:
    """ TODO """
    INTERNAL_ALIAS_SETTING_NAME = "[MANAGED BY SQUIRE] Internal Alias"

    def __init__(self, mailcow_host: str, mailcow_api_key: str):
        self.client = MailcowAPIClient(mailcow_host, mailcow_api_key)

    def _get_rspamd_internal_alias_setting(self) -> Optional[RspamdSettings]:
        """ Gets the Rspamd setting (if it exists) that is used by Squire
            to mark email aliases as 'internal'. Squire recognises which
            Rspamd setting to use based on the setting's name
            (`self.INTERNAL_ALIAS_SETTING_NAME`).
        """
        # Fetch all Rspamd settings
        settings = self.client.get_rspamd_setting_all()
        for setting in settings:
            # Setting description matches the one we normally set
            if setting.desc == self.INTERNAL_ALIAS_SETTING_NAME:
                return setting
        return None

    def set_internal_addresses(self, addresses: list[str]) -> None:
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
            self.client.create_rspamd_setting(setting)
        else:
            # Setting exists but should be updated
            setting.content = setting_content
            self.client.update_rspamd_setting(setting)

