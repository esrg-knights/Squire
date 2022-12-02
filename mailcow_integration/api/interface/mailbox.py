from dataclasses import dataclass
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
  force_pw_update: bool
  tls_enforce_in: bool
  tls_enforce_out: bool
  sogo_access: bool
  imap_access: bool
  pop3_access: bool
  smtp_access: bool
  xmpp_access: bool
  xmpp_admin: bool
  mailbox_format: str # ??? E.g. 'maildir:'
  quarantine_notification: QuarantineNotification
  quarantine_category: QuarantaineNotificationCategory

  @classmethod
  def from_json(cls, json: dict) -> 'MailboxAttributes':
      json.update({
          'force_pw_update': bool(json['force_pw_update']),
          'tls_enforce_in': bool(json['tls_enforce_in']),
          'tls_enforce_out': bool(json['tls_enforce_out']),
          'sogo_access': bool(json['sogo_access']),
          'imap_access': bool(json['imap_access']),
          'pop3_access': bool(json['pop3_access']),
          'smtp_access': bool(json['smtp_access']),
          'xmpp_access': bool(json['xmpp_access']),
          'xmpp_admin': bool(json['xmpp_admin']),
          'quarantine_notification': QuarantineNotification(json['quarantine_notification']),
          'quarantine_category': QuarantaineNotificationCategory(json['quarantine_category']),
      })
      return cls(**json)


@dataclass
class MailcowMailbox(MailcowAPIResponse):
    """ Mailcow Mailbox """
    username: str # Username is the id
    name: str # Name appearing when sending an email
    local_part: str # everything before the @example.com
    domain: str

    active: MailboxStatus
    active_int: int # ??? Always identical to active

    messages: int # Number of messages in the mailbox
    quota: int # in bytes; 0 for infinite
    quota_used: int # in bytes
    percent_in_use: Optional[int] # from 0-100, or None if N/A
    max_new_quota: int # in bytes; maximum possible quota

    rl: bool # ???
    rl_scope: str # ??? E.g. 'domain'
    is_relayed: bool # ???

    last_imap_login: Optional[datetime]
    last_smtp_login: Optional[datetime]
    last_pop3_login: Optional[datetime]

    domain_xmpp: int
    domain_xmpp_prefix: str # ???

    spam_aliases: int # ???
    pushover_active: bool # Push notification settings
    percent_class: str # ??? E.g. 'success'

    attributes: MailboxAttributes

    @classmethod
    def from_json(cls, json: dict) -> 'MailcowMailbox':
        json.update({
            'active': MailboxStatus(json['active']),
            'percent_in_use': int(json['percent_in_use']) if json['percent_in_use'] != "-" else None,
            'rl': bool(json['rl']),
            'is_relayed': bool(json['is_relayed']),
            'last_imap_login': datetime.fromtimestamp(int(json['last_imap_login'])) if json['last_imap_login'] != "0" else None,
            'last_smtp_login': datetime.fromtimestamp(int(json['last_smtp_login'])) if json['last_smtp_login'] != "0" else None,
            'last_pop3_login': datetime.fromtimestamp(int(json['last_pop3_login'])) if json['last_pop3_login'] != "0" else None,
            'pushover_active': bool(json['pushover_active']),
            'attributes': MailboxAttributes.from_json(json['attributes'])
        })
        return cls(**json)
