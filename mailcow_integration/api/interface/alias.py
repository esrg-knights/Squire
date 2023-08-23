from enum import Enum
from typing import Optional, List

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
    def from_json(cls, json: dict) -> "MailcowAlias":
        json.update(
            {
                "goto": json["goto"].split(","),
                "active": bool(json["active"]),
                "is_catch_all": bool(json["is_catch_all"]),
                "public_comment": json["public_comment"] or "",
                "private_comment": json["private_comment"] or "",
                "sogo_visible": bool(json["sogo_visible"]),
                "created": datetime.fromisoformat(json["created"]),
                "modified": datetime.fromisoformat(json["modified"]) if json["modified"] is not None else None,
            }
        )
        return cls(**json)
