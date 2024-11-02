from enum import Enum
import json
import logging
import requests
from typing import Generator, List, Optional, Union

from mailcow_integration.api.exceptions import *
from mailcow_integration.api.interface.alias import AliasType, MailcowAlias
from mailcow_integration.api.interface.mailbox import MailcowMailbox
from mailcow_integration.api.interface.rspamd import RspamdSettings

logger = logging.getLogger(__name__)


class RequestType(Enum):
    """Different types of requests that can be made to the Mailcow API"""

    GET = "get"
    POST = "post"


class MailcowAPIClient:
    """A client that connects to and acts as a wrapper for the Mailcow API (v1).
    It is by no means meant to be a complete representation of the (poorly
    documented) API, but rather only includes functionality needed for Squire.

    For an incomplete overview of the Mailcow API, see: https://mailcow.docs.apiary.io

    In order to connect to a `host`'s API, an `api_key` needs to be generated in the
    Mailcow admin. Additionally, the API needs to be activated, and the ipv4 and/or ipv6
    addresses of the client needs to be added to an IP whitelist (alternatively, the
    IP whitelist can be disabled entirely).
    """

    API_FORMAT = "%(host)s/api/v1/"

    def __init__(self, host: str, api_key: str):
        self.host = host
        self.api_key = api_key

    def _get_headers(self) -> dict:
        """Retrieves the headers required to fetch info from the Mailcow API."""
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "user-agent": "squire/1.0.0",
        }

    def _verify_response_content(self, content: dict, request_url: str) -> None:
        """Checks some response data, and generates an appropriate exception based on it"""
        if content.get("type", None) == "error":
            # API returned an error
            if content.get("msg", None) == "authentication failed":
                # Invalid API key
                raise MailcowAuthException(f"{request_url}: {content['msg']}")
            elif content.get("msg", "").startswith("API read/write access denied"):
                raise MailcowAPIReadWriteAccessDenied(f"{request_url}: {content['msg']}")
            elif content.get("msg", "").startswith("api access denied"):
                # IP is not whitelisted
                raise MailcowAPIAccessDenied(f"{request_url}: {content['msg']}")
            elif content.get("msg", None) == "route not found":
                raise MailcowRouteNotFoundException(f"{request_url}: {content['msg']}")
            else:
                # Some other error (should not happen)
                logger.error(content)
                raise MailcowException(f"{request_url}: {content['msg']}")
        elif content.get("type", None) == "danger":
            # Unknown exception occurred. E.g. invalid parameters passed to POST
            logger.error(content)
            raise MailcowException(f"{request_url}: {content['msg']}")
        elif not content:
            # API returned an empty response
            raise MailcowIDNotFoundException(f"{request_url} returned an empty response.")

    def _make_request(
        self, url: str, request_type: RequestType = RequestType.GET, params: dict = None, data: dict = None
    ) -> Union[dict, list]:
        """Makes a request to the endpoint specified by `url`, with some parameters `params` and some `data`."""
        url = self.API_FORMAT % {"host": self.host} + url
        logger.info(f"Request made to: {url}")
        res = requests.request(request_type.value, url, params=params, data=data, headers=self._get_headers())

        try:
            content = res.json()
        except json.JSONDecodeError:
            # Content did not have valid formatting
            raise MailcowException(f"Unexpected response for {url}: {res.content}")

        if isinstance(content, list):
            # Responses are sometimes packed in a list (e.g., when updating multiple entries at the same time)
            for c in content:
                self._verify_response_content(c, url)
        elif isinstance(content, dict):
            self._verify_response_content(content, url)

        return content

    ################
    # ALIASES
    ################
    def get_alias_all(self) -> Generator[Optional[MailcowAlias], None, None]:
        """Gets a list of all email aliases"""
        content = self._make_request(f"get/alias/all")
        return map(lambda alias: MailcowAlias.from_json(alias), content)

    def get_alias(self, id: int) -> Optional[MailcowAlias]:
        """Gets an email alias with a specific id"""
        content = self._make_request(f"get/alias/{id}")
        return MailcowAlias.from_json(content)

    def update_alias(self, alias: MailcowAlias) -> dict:
        """Updates an alias"""
        assert alias.id is not None

        data = {
            "items": [alias.id],
            "attr": {
                "address": alias.address,
                "active": int(alias.active),
                "public_comment": alias.public_comment,
                "private_comment": alias.private_comment,
                "sogo_visible": int(alias.sogo_visible),
            },
        }

        # goto address
        alias_type = alias.get_type()
        if alias_type == AliasType.NORMAL:
            data["attr"]["goto"] = ",".join(alias.goto)
        elif alias_type == AliasType.HAM:
            data["attr"]["goto_ham"] = 1
        elif alias_type == AliasType.SPAM:
            data["attr"]["goto_spam"] = 1
        elif alias_type == AliasType.SILENT_DISCARD:
            data["attr"]["goto_null"] = 1

        data = json.dumps(data)
        return self._make_request(f"edit/alias/{alias.id}", request_type=RequestType.POST, data=data)

    def create_alias(self, alias: MailcowAlias) -> dict:
        """Creates a new alias"""
        assert alias.id is None
        data = {
            "address": alias.address,
            "active": int(alias.active),
            "public_comment": alias.public_comment,
            "private_comment": alias.private_comment,
            "sogo_visible": int(alias.sogo_visible),
        }
        # goto address
        alias_type = alias.get_type()
        if alias_type == AliasType.NORMAL:
            data["goto"] = ",".join(alias.goto)
        elif alias_type == AliasType.HAM:
            data["goto_ham"] = 1
        elif alias_type == AliasType.SPAM:
            data["goto_spam"] = 1
        elif alias_type == AliasType.SILENT_DISCARD:
            data["goto_null"] = 1

        data = json.dumps(data)
        return self._make_request(f"add/alias", request_type=RequestType.POST, data=data)

    def delete_aliases(self, aliases: List[MailcowAlias]) -> dict:
        """Deletes a collection of aliases"""
        assert aliases
        assert all(alias.id is not None for alias in aliases)

        # NOTE: This does not match up with the requests made in the Mailcow admin panel,
        #   which has the format:
        #   { items: [<id1>, <id2>, ...] }
        data = [str(alias.id) for alias in aliases]
        data = json.dumps(data)
        return self._make_request("delete/alias", request_type=RequestType.POST, data=data)

    ################
    # MAILBOXES
    ################
    def get_mailbox_all(self) -> Generator[Optional[MailcowMailbox], None, None]:
        """Gets a list of all mailboxes"""
        content = self._make_request(f"get/mailbox/all")
        return map(lambda mailbox: MailcowMailbox.from_json(mailbox), content)

    ################
    # RSPAMD SETTINGS (undocumented API)
    ################
    def get_rspamd_setting_all(self) -> Generator[Optional[RspamdSettings], None, None]:
        """Gets all Rspamd settings maps"""
        content = self._make_request("get/rsetting/all")
        return map(lambda rspamdsetting: RspamdSettings.from_json(rspamdsetting), content)

    def get_rspamd_setting(self, id: int) -> Optional[RspamdSettings]:
        """Gets an Rspamd settings map with a specific id"""
        content = self._make_request(f"get/rsetting/{id}")
        return RspamdSettings.from_json(content)

    def update_rspamd_setting(self, setting: RspamdSettings) -> dict:
        """Updates the RspamdSetting associated to the given ID with the given data"""
        assert setting.id is not None
        data = json.dumps(
            {
                "items": [setting.id],
                "attr": {
                    "active": int(setting.active),
                    "desc": setting.desc,
                    "content": setting.content,
                },
            }
        )
        # NOTE: API endpoint omits rsetting id
        return self._make_request(f"edit/rsetting", request_type=RequestType.POST, data=data)

    def create_rspamd_setting(self, setting: RspamdSettings) -> dict:
        """Creates a new Rspamd setting"""
        assert setting.id is None
        data = json.dumps(
            {
                "desc": setting.desc,
                "content": setting.content,
                "active": int(setting.active),
            }
        )
        return self._make_request(f"add/rsetting", request_type=RequestType.POST, data=data)
