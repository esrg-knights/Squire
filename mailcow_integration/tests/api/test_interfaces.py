from copy import deepcopy
from datetime import datetime
from unittest import TestCase

from mailcow_integration.api.interface.alias import AliasType, MailcowAlias
from mailcow_integration.api.interface.mailbox import (
    MailboxStatus,
    MailcowMailbox,
    QuarantaineNotificationCategory,
    QuarantineNotification,
)
from mailcow_integration.api.interface.rspamd import RspamdSettings


def get_alias_json():
    """Gets valid json for a MailcowAlias"""
    return deepcopy(
        {
            "in_primary_domain": "",
            "id": 42,
            "domain": "example.com",
            "public_comment": "[DEV][MANAGED BY SQUIRE] Members Alias",
            "private_comment": None,
            "goto": "bar@example.com,baz@example.com",
            "address": "foo@example.com",
            "is_catch_all": 0,
            "active": 1,
            "active_int": 1,
            "sogo_visible": 0,
            "sogo_visible_int": 0,
            "created": "2022-11-21 14:15:24",
            "modified": "2022-12-03 17:09:42",
        }
    )


def get_mailbox_json():
    """Gets valid json for a MailcowMailbox"""
    return deepcopy(
        {
            "max_new_quota": 123456789,
            "username": "foo@example.com",
            "rl": False,
            "rl_scope": "domain",
            "is_relayed": 0,
            "name": "Mr. Foo",
            "last_imap_login": "1665675411",
            "last_smtp_login": "0",
            "last_pop3_login": "0",
            "active": 1,
            "active_int": 1,
            "domain": "example.com",
            "domain_xmpp": 0,
            "domain_xmpp_prefix": "im",
            "local_part": "foo",
            "quota": 1048576,
            "attributes": {
                "force_pw_update": "0",
                "tls_enforce_in": "0",
                "tls_enforce_out": "0",
                "sogo_access": "1",
                "mailbox_format": "maildir:",
                "quarantine_notification": "never",
                "xmpp_access": "1",
                "xmpp_admin": "0",
                "imap_access": "1",
                "pop3_access": "1",
                "smtp_access": "1",
                "quarantine_category": "reject",
            },
            "quota_used": 94129,
            "percent_in_use": 9,
            "messages": 17,
            "spam_aliases": 0,
            "pushover_active": 0,
            "percent_class": "success",
        }
    )


def get_rspamd_json():
    """Gets valid json for an Rspamd rule"""
    return deepcopy(
        {
            "id": 1,
            "desc": "[DEV][MANAGED BY SQUIRE] Internal Alias",
            "content": "# MANAGED BY SQUIRE - DO NOT MODIFY;\r\nfoo faa rules;\r\nyet another rule;\r\n]",
            "active": 0,
        }
    )


class MailcowInterfacesTest(TestCase):
    """Tests various Mailcow interfaces"""

    def test_alias_type(self):
        """AliasType is returned correctly"""
        self.assertEqual(MailcowAlias("foo@example.com", ["bar@example.com"]).get_type(), AliasType.NORMAL)
        self.assertEqual(MailcowAlias("foo@example.com", ["null@localhost"]).get_type(), AliasType.SILENT_DISCARD)
        self.assertEqual(MailcowAlias("foo@example.com", ["spam@localhost"]).get_type(), AliasType.SPAM)
        self.assertEqual(MailcowAlias("foo@example.com", ["ham@localhost"]).get_type(), AliasType.HAM)

    def test_alias_from_json(self):
        """Alias JSON correctly converted to object"""
        alias = MailcowAlias.from_json(get_alias_json())
        self.assertListEqual(alias.goto, ["bar@example.com", "baz@example.com"])
        self.assertEqual(alias.active, True)
        self.assertEqual(alias.is_catch_all, False)
        self.assertEqual(alias.private_comment, "")
        self.assertEqual(alias.created, datetime.fromisoformat("2022-11-21 14:15:24"))
        self.assertEqual(alias.modified, datetime.fromisoformat("2022-12-03 17:09:42"))

    def test_mailbox_from_json(self):
        """Mailbox JSON correctly converted to object"""
        data = get_mailbox_json()
        mailbox = MailcowMailbox.from_json(deepcopy(data))

        self.assertEqual(mailbox.active, MailboxStatus.ACTIVE)
        self.assertEqual(mailbox.percent_in_use, 9)
        self.assertEqual(mailbox.rl, False)
        # Last login done at some point
        self.assertEqual(mailbox.last_imap_login, datetime.fromtimestamp(int(1665675411)))
        # No login ever
        self.assertIsNone(mailbox.last_smtp_login)
        self.assertIsNone(mailbox.last_pop3_login)
        self.assertEqual(mailbox.pushover_active, False)

        # Mailbox attributes
        self.assertEqual(mailbox.attributes.force_pw_update, False)
        self.assertEqual(mailbox.attributes.tls_enforce_in, False)
        self.assertEqual(mailbox.attributes.tls_enforce_out, False)
        self.assertEqual(mailbox.attributes.sogo_access, True)
        self.assertEqual(mailbox.attributes.imap_access, True)
        self.assertEqual(mailbox.attributes.pop3_access, True)
        self.assertEqual(mailbox.attributes.smtp_access, True)
        self.assertEqual(mailbox.attributes.xmpp_access, True)
        self.assertEqual(mailbox.attributes.xmpp_admin, False)
        self.assertEqual(mailbox.attributes.quarantine_notification, QuarantineNotification.NEVER)
        self.assertEqual(mailbox.attributes.quarantine_category, QuarantaineNotificationCategory.REJECT)

        # No quota
        data["percent_in_use"] = "- "
        mailbox = MailcowMailbox.from_json(data)
        self.assertIsNone(mailbox.percent_in_use)

    def test_rspamd_from_json(self):
        """Rspamd Setting JSON correctly converted to object"""
        setting = RspamdSettings.from_json(get_rspamd_json())
        self.assertEqual(setting.id, 1)
        self.assertEqual(setting.active, False)
        self.assertEqual(False, 0)
