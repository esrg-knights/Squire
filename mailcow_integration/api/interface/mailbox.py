from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from mailcow_integration.api.interface.base import MailcowAPIResponse

class MailboxStatus(Enum):
    """ Active status of a Mailcow Mailbox """
    INACTIVE = 0
    ACTIVE = 1
    DISALLOW_LOGIN = 2

class QuarantineNotification(Enum):
    """ Quarantine Notification intervals """
    NEVER = "never"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"

class QuarantaineNotificationCategory(Enum):
    """ Quarantine Notification categories """
    REJECT = "reject" # Rejected
    JUNK = "add_header" # Junk folder
    ALL = "all" # All categories

@dataclass
class MailboxAttributes(MailcowAPIResponse):
    """ Additional Mailcow Mailbox attributes """
    force_pw_update: bool = False
    tls_enforce_in: bool = False
    tls_enforce_out: bool = False
    sogo_access: bool = True
    imap_access: bool = True
    pop3_access: bool = True
    smtp_access: bool = True
    xmpp_access: bool = False
    xmpp_admin: bool = False
    mailbox_format: str = "maildir:" # ??? E.g. 'maildir:'
    quarantine_notification: QuarantineNotification = QuarantineNotification.NEVER
    quarantine_category: QuarantaineNotificationCategory = QuarantaineNotificationCategory.REJECT

    @classmethod
    def from_json(cls, json: dict) -> 'MailboxAttributes':
        json.update({
            'force_pw_update': json['force_pw_update'] != "0",
            'tls_enforce_in': json['tls_enforce_in'] != "0",
            'tls_enforce_out': json['tls_enforce_out'] != "0",
            'sogo_access': json['sogo_access'] != "0",
            'imap_access': json['imap_access'] != "0",
            'pop3_access': json['pop3_access'] != "0",
            'smtp_access': json['smtp_access'] != "0",
            'xmpp_access': json['xmpp_access'] != "0",
            'xmpp_admin': json['xmpp_admin'] != "0",
            'quarantine_notification': QuarantineNotification(json['quarantine_notification']),
            'quarantine_category': QuarantaineNotificationCategory(json['quarantine_category']),
        })
        return cls(**json)


@dataclass
class MailcowMailbox(MailcowAPIResponse):
    """ Mailcow Mailbox """
    username: str # Username is the id
    name: str # Name appearing when sending an email
    local_part: str = None # everything before the @example.com
    domain: str = None

    active: MailboxStatus = MailboxStatus.ACTIVE
    active_int: int = None # ??? Always identical to active

    messages: int = 0 # Number of messages in the mailbox
    quota: int = 0 # in bytes; 0 for infinite
    quota_used: int = 0 # in bytes
    percent_in_use: Optional[int] = None # from 0-100, or None if N/A
    max_new_quota: int = 0 # in bytes; maximum possible quota

    rl: bool = False # ???
    rl_scope: str = "domain" # ??? E.g. 'domain'
    is_relayed: bool = False # ???

    last_imap_login: Optional[datetime] = None
    last_smtp_login: Optional[datetime] = None
    last_pop3_login: Optional[datetime] = None

    domain_xmpp: int = 0
    domain_xmpp_prefix: str = "" # ???

    spam_aliases: int = 0 # ???
    pushover_active: bool = False # Push notification settings
    percent_class: str = "success" # ??? E.g. 'success'

    attributes: MailboxAttributes = field(default_factory=MailboxAttributes)

    def __post_init__(self):
        index = self.username.find("@")
        if self.local_part is None:
            self.local_part = self.username[index + 1:]
        index = min(index, 0)
        if self.domain is None:
            self.domain = self.username[:index]

        if self.active_int is None:
            self.active_int = self.active.value

    @classmethod
    def from_json(cls, json: dict) -> 'MailcowMailbox':
        json.update({
            'active': MailboxStatus(json['active']),
            'percent_in_use': int(json['percent_in_use']) if json['percent_in_use'] != "- " else None,
            'rl': bool(json['rl']),
            'is_relayed': bool(json['is_relayed']),
            'last_imap_login': datetime.fromtimestamp(int(json['last_imap_login'])) if json['last_imap_login'] != "0" else None,
            'last_smtp_login': datetime.fromtimestamp(int(json['last_smtp_login'])) if json['last_smtp_login'] != "0" else None,
            'last_pop3_login': datetime.fromtimestamp(int(json['last_pop3_login'])) if json['last_pop3_login'] != "0" else None,
            'pushover_active': bool(json['pushover_active']),
            'attributes': MailboxAttributes.from_json(json['attributes'])
        })
        return cls(**json)
