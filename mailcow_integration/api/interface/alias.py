from enum import Enum
from typing import Optional, List, Set

from datetime import datetime
from dataclasses import dataclass

from mailcow_integration.api.interface.base import MailcowAPIResponse


class AliasType(Enum):
    NORMAL = "internal-mails"
    SILENT_DISCARD = "null@localhost"
    HAM = "ham@localhost"
    SPAM = "spam@localhost"


@dataclass
class MailcowAlias(MailcowAPIResponse):
    """Mailcow Alias"""

    address: str
    goto: List[str]

    id: Optional[int] = None
    active: bool = True
    active_int: int = None  # ???

    in_primary_domain: str = ""
    domain: str = ""
    is_catch_all: bool = False

    public_comment: str = ""
    private_comment: str = ""

    sogo_visible: bool = True  # Alias can be used as a selectable sender in SOGo
    sogo_visible_int: int = None  # ???

    created: Optional[datetime] = None
    modified: Optional[datetime] = None

    _cleanable_bools = ("active", "is_catch_all", "sogo_visible")
    _cleanable_ints = ("id", "active_int", "sogo_visible_int")
    _cleanable_strings = ("in_primary_domain", "domain")
    _cleanable_datetimes = ("created",)

    def __post_init__(self):
        if self.active_int is None:
            self.active_int = int(self.active)

        if self.sogo_visible_int is None:
            self.sogo_visible_int = int(self.sogo_visible)

    def get_type(self) -> AliasType:
        if len(self.goto) == 1:
            try:
                return AliasType(self.goto[0])
            except ValueError:
                pass
        return AliasType.NORMAL

    @classmethod
    def clean(cls, json: dict, extra_keys: Set[str] = None) -> dict:
        address = json.get("address", None)
        if address is None:
            cls._issue_warning("address", address)
            raise AttributeError(f"address was not provided when creating {cls.__name__}")

        # Goto-addresses are comma-separated strings
        goto = json.get("goto", None)
        if goto is None or not isinstance(goto, str):
            cls._issue_warning("goto", goto, "list")
            raise AttributeError(f"goto was not provided or had an invalid value when creating {cls.__name__}")

        new_json = {
            "address": address,
            "goto": goto.split(","),
        }

        # Modified can be returned as None
        if "modified" not in json:
            cls._issue_warning("modified", None, "ISO-datetime (or None)")
        else:
            modified = json.get("modified")
            if modified is not None:
                modified = cls._parse_as_dt("modified", json)
            new_json["modified"] = modified

        # Same for the private/public comment
        if "public_comment" not in json:
            cls._issue_warning("public_comment", None, "string (or None)")
        else:
            new_json["public_comment"] = str(json.get("public_comment") or "")

        if "private_comment" not in json:
            cls._issue_warning("private_comment", None, "string (or None)")
        else:
            new_json["private_comment"] = str(json.get("private_comment") or "")

        extra_keys = extra_keys or set()
        new_json.update(**super().clean(json, extra_keys=new_json.keys() | extra_keys))
        return new_json
