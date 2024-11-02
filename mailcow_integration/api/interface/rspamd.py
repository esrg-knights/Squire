from dataclasses import dataclass
from typing import Optional, Set

from mailcow_integration.api.interface.base import MailcowAPIResponse


@dataclass
class RspamdSettings(MailcowAPIResponse):
    """Rspamd Settings"""

    id: Optional[int]
    desc: str
    content: str  # rspamd configuration
    active: bool = True

    _cleanable_bools = ("active",)
    _cleanable_ints = ("id",)
    _cleanable_strings = ("desc", "content")
