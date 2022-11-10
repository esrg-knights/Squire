from dataclasses import dataclass
from typing import Optional

from mailcow_integration.api.interface.base import MailcowAPIResponse

@dataclass
class RspamdSettings(MailcowAPIResponse):
    """ Rspamd Settings """
    id: Optional[int]
    desc: str
    content: str # rspamd configuration
    active: bool = True

    @classmethod
    def from_json(cls, json: dict) -> 'RspamdSettings':
        json.update({
            'active': bool(json['active'])
        })
        return cls(**json)
