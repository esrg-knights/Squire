from enum import Enum
import json
from typing import List
import requests

from mailcow_integration.api.exceptions import *
from mailcow_integration.api.interface.alias import AliasType, MailcowAlias
from mailcow_integration.api.interface.rspamd import RspamdSettings

class RequestType(Enum):
    GET = "get"
    POST = "post"

class MailcowAPIClient:
    """ TODO """
    API_FORMAT = "https://%(host)s/api/v1/"

    def __init__(self, host: str, api_key: str):
        self.host = host
        self.api_key = api_key

    def _get_headers(self):
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "user-agent": "squire/1.0.0",
        }

    def _make_request(self, url: str, request_type: RequestType=RequestType.GET, params: dict = None, data: dict = None) -> requests.Response:
        url = self.API_FORMAT % {'host': self.host} + url
        print(url)
        res = requests.request(request_type.value, url, params=params, data=data, headers=self._get_headers())
        content = json.loads(res.content)

        if isinstance(content, dict):
            if content.get('type', None) == "error":
                # API returned an error
                if content.get('msg', None) == "authentication failed":
                    # Invalid API key
                    raise MailcowAuthException(content['msg'])
                elif content.get("msg", "").startswith("API read/write access denied"):
                    raise MailcowAPIReadWriteAccessDenied(content['msg'])
                elif content.get('msg', "").startswith("api access denied"):
                    # IP is not whitelisted
                    raise MailcowAPIAccessDenied(content['msg'])
                elif content.get('msg', None) == "route not found":
                    raise MailcowRouteNotFoundException(content['msg'])
                else:
                    # Some other error (should not happen)
                    raise MailcowException(content['msg'])
            elif content.get('type', None) == 'danger':
                # Unknown exception occurred. E.g. invalid parameters passed to POST
                raise MailcowException(content['msg'])
            elif not content:
                # API returned an empty response
                raise MailcowIDNotFoundException(f'{url} returned an empty response.')
        return res

    ################
    # ALIASES
    ################
    def get_alias_all(self) -> List[MailcowAlias]:
        """ Gets a list of all email aliases """
        res = self._make_request(f"get/alias/all")
        return map(lambda alias: MailcowAlias.from_json(alias), json.loads(res.content))

    def get_alias(self, id: int) -> MailcowAlias:
        """ Gets an email alias with a specific id """
        res = self._make_request(f"get/alias/{id}")
        content: dict = json.loads(res.content)
        return MailcowAlias.from_json(content)

    def update_alias(self, alias: MailcowAlias) -> requests.Response:
        """ Updates an alias """
        data = {
            'items': [alias.id],
            'attr': {
                'address': alias.address,
                'active': int(alias.active),
                'public_comment': alias.public_comment,
                'private_comment': alias.private_comment,
                'sogo_visible': int(alias.sogo_visible),
            }
        }

        # goto address
        alias_type = alias.get_type()
        if alias_type == AliasType.NORMAL:
            data['attr']['goto'] = ",".join(alias.goto)
        elif alias_type == AliasType.HAM:
            data['attr']['goto_ham'] = 1
        elif alias_type == AliasType.SPAM:
            data['attr']['goto_spam'] = 1
        elif alias_type == AliasType.SILENT_DISCARD:
            data['attr']['goto_null'] = 1

        data = json.dumps(data)
        return self._make_request(f"edit/alias/{id}", request_type=RequestType.POST, data=data)

    def create_alias(self, alias: MailcowAlias) -> requests.Response:
        """ Creates a new alias """
        data = {
            'address': alias.address,
            'active': int(alias.active),
            'public_comment': alias.public_comment,
            'private_comment': alias.private_comment,
            'sogo_visible': int(alias.sogo_visible),
        }
        # goto address
        alias_type = alias.get_type()
        if alias_type == AliasType.NORMAL:
            data['goto'] = ",".join(alias.goto)
        elif alias_type == AliasType.HAM:
            data['goto_ham'] = 1
        elif alias_type == AliasType.SPAM:
            data['goto_spam'] = 1
        elif alias_type == AliasType.SILENT_DISCARD:
            data['goto_null'] = 1

        data = json.dumps(data)
        return self._make_request(f"add/alias", request_type=RequestType.POST, data=data)

    ################
    # RSPAMD SETTINGS
    ################
    def get_rspamd_setting_all(self) -> List[RspamdSettings]:
        """ Gets all Rspamd settings maps """
        res = self._make_request("get/rsetting/all")
        return map(lambda rspamdsetting: RspamdSettings.from_json(rspamdsetting), json.loads(res.content))

    def get_rspamd_setting(self, id: int) -> RspamdSettings:
        """ Gets an Rspamd settings map with a specific id """
        res = self._make_request(f"get/rsetting/{id}")
        return RspamdSettings.from_json(json.loads(res.content))

    def update_rspamd_setting(self, setting: RspamdSettings) -> requests.Response:
        """ Updates the RspamdSetting associated to the given ID with the given data """
        data = json.dumps({
            'items': [setting.id],
            'attr': {
                'active': int(setting.active),
                'desc': setting.desc,
                'content': setting.content,
            }
        })
        return self._make_request(f"edit/rsetting", request_type=RequestType.POST, data=data)

    def create_rspamd_setting(self, setting: RspamdSettings) -> requests.Response:
        """ Creates a new Rspamd setting """
        data = json.dumps({
            'desc': setting.desc,
            'content': setting.content,
            'active': int(setting.active),
        })
        return self._make_request(f"add/rsetting", request_type=RequestType.POST, data=data)
