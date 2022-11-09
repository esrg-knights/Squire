from dataclasses import dataclass

from mailcow_integration.interface.base import MailcowAPIResponse

@dataclass
class RspamdSettings(MailcowAPIResponse):
    """ Rspamd Settings """
    id: int
    desc: str
    content: str # rspamd configuration
    active: bool

    @classmethod
    def from_json(cls, json: dict) -> 'RspamdSettings':
        json.update({
            'active': bool(json['active'])
        })
        return cls(**json)
