from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from typing import Dict, List, Optional, Set

from mailcow_integration.api.interface.base import MailcowAPIResponse


class MailboxStatus(Enum):
    """Active status of a Mailcow Mailbox"""

    INACTIVE = 0
    ACTIVE = 1
    DISALLOW_LOGIN = 2


class QuarantineNotification(Enum):
    """Quarantine Notification intervals"""

    NEVER = "never"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


class QuarantaineNotificationCategory(Enum):
    """Quarantine Notification categories"""

    REJECT = "reject"  # Rejected
    JUNK = "add_header"  # Junk folder
    ALL = "all"  # All categories


@dataclass
class MailboxAttributes(MailcowAPIResponse):
    """Additional Mailcow Mailbox attributes"""

    force_pw_update: bool = False
    tls_enforce_in: bool = False
    tls_enforce_out: bool = False
    sogo_access: bool = True
    imap_access: bool = True
    pop3_access: bool = True
    smtp_access: bool = True
    xmpp_access: bool = False
    xmpp_admin: bool = False
    mailbox_format: str = "maildir:"  # ??? E.g. 'maildir:'
    quarantine_notification: QuarantineNotification = QuarantineNotification.NEVER
    quarantine_category: QuarantaineNotificationCategory = QuarantaineNotificationCategory.REJECT
    passwd_update: Optional[datetime] = None  # When a password was last updated
    relayhost: bool = False
    sieve_access: bool = False
    recovery_email: str = ""

    _cleanable_bools = (
        "force_pw_update",
        "tls_enforce_in",
        "tls_enforce_out",
        "sogo_access",
        "imap_access",
        "pop3_access",
        "smtp_access",
        "xmpp_access",
        "xmpp_admin",
        "relayhost",
        "sieve_access",
    )
    _cleanable_strings = ("mailbox_format",)
    _cleanable_datetimes = ("passwd_update",)

    @classmethod
    def clean(cls, json: dict, extra_keys: Set[str] = None):
        new_json = {}

        # Quarantine
        notif = cls._parse_as_enum("quarantine_notification", json, QuarantineNotification)
        if notif is not None:
            new_json["quarantine_notification"] = notif

        cat = cls._parse_as_enum("quarantine_category", json, QuarantaineNotificationCategory)
        if cat is not None:
            new_json["quarantine_category"] = cat

        # Recovery email can be '' or absent from the JSON when it is not set
        rec = json.get("recovery_email", None)
        if rec is not None:
            new_json["recovery_email"] = str(rec)

        extra_keys = extra_keys or set()
        new_json.update(**super().clean(json, extra_keys=new_json.keys() | extra_keys))

        return new_json


@dataclass
class MailcowMailbox(MailcowAPIResponse):
    """Mailcow Mailbox"""

    username: str  # Username is the id
    name: str  # Name appearing when sending an email
    local_part: str = None  # everything before the @example.com
    domain: str = None

    active: MailboxStatus = MailboxStatus.ACTIVE
    active_int: int = None  # ??? Always identical to active
    created: Optional[datetime] = None
    modified: Optional[datetime] = None

    messages: int = 0  # Number of messages in the mailbox
    quota: int = 0  # in bytes; 0 for infinite
    quota_used: int = 0  # in bytes
    percent_in_use: Optional[int] = None  # from 0-100, or None if N/A
    max_new_quota: int = 0  # in bytes; maximum possible quota

    rl: bool = False  # ???
    rl_scope: str = "domain"  # ??? E.g. 'domain'
    is_relayed: bool = False  # ???

    last_imap_login: Optional[datetime] = None
    last_smtp_login: Optional[datetime] = None
    last_pop3_login: Optional[datetime] = None

    spam_aliases: int = 0  # ???
    pushover_active: bool = False  # Push notification settings
    percent_class: str = "success"  # ??? E.g. 'success'

    attributes: MailboxAttributes = field(default_factory=MailboxAttributes)
    custom_attributes: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    _cleanable_bools = ("rl", "is_relayed", "pushover_active")
    _cleanable_strings = ("local_part", "domain", "rl_scope", "percent_class")
    _cleanable_ints = (
        "active_int",
        "messages",
        "quota",
        "quota_used",
        "max_new_quota",
        "spam_aliases",
    )
    _cleanable_datetimes = ("created", "modified", "last_imap_login", "last_smtp_login", "last_pop3_login")

    def __post_init__(self):
        index = self.username.find("@")
        if self.local_part is None:
            self.local_part = self.username[index + 1 :]
        index = min(index, 0)
        if self.domain is None:
            self.domain = self.username[:index]

        if self.active_int is None:
            self.active_int = self.active.value

    @classmethod
    def clean(cls, json: dict, extra_keys: Set[str] = None):
        username = json.get("username", None)
        name = json.get("name", None)
        if username is None:
            cls._issue_warning("username", username)
            raise AttributeError(f"username was not provided when creating {cls.__name__}")
        if name is None:
            cls._issue_warning("name", name)
            raise AttributeError(f"name was not provided when creating {cls.__name__}")

        # Validate custom attributes
        custom_attributes = json.get("custom_attributes", None)
        if isinstance(custom_attributes, dict):
            custom_attributes = {str(k): str(v) for k, v in custom_attributes.items()}
        else:
            if not isinstance(custom_attributes, list) or custom_attributes:
                # If no custom_attributes are set, the API returns it as []
                cls._issue_warning("custom_attributes", custom_attributes, "dict")
            custom_attributes = {}

        # Validate tags
        tags = json.get("tags", [])
        if isinstance(tags, list):
            tags = [str(tag) for tag in tags]
        else:
            cls._issue_warning("tags", tags, "list")
            tags = []

        new_json = {
            "username": username,
            "name": name,
            "attributes": MailboxAttributes.from_json(json.get("attributes", {})) or MailboxAttributes(),
            "custom_attributes": custom_attributes,
            "tags": tags,
        }

        # Active-status
        active = cls._parse_as_enum("active", json, MailboxStatus)
        if active is not None:
            new_json["active"] = active

        # Mailbox percentage is a number, or "- " if unlimited
        percent = json.get("percent_in_use")
        if percent == "- ":
            new_json["percent_in_use"] = None
        elif not isinstance(percent, int):
            cls._issue_warning("percent_in_use", percent, "int (or '- ')")
        else:
            new_json["percent_in_use"] = percent

        extra_keys = extra_keys or set()
        new_json.update(**super().clean(json, extra_keys=new_json.keys() | extra_keys))

        return new_json
