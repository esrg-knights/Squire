import json
from dataclasses import dataclass
from typing import Type, TypeVar, cast
from typing_extensions import Self

from google.oauth2 import service_account

from gworkspace_integration.api.services.directory_service import DirectoryService, GoogleAPIService


@dataclass
class GoogleWorkspaceSettings:
    """
    Settings for connecting to the google workspace API.
    - `service_account_token_path`: A service-account token
    - `scopes`: Scopes corresponding to the token
    - `domain`: Limit interactions to users/groups of this domain, if applicable
    - `directory_admin_username`: Username of an admin account. This is required to use the directory API to manage users/groups
    """

    service_account_token_path: str
    scopes: list[str]
    domain: str
    members_ou: str
    directory_admin_username: str

    @classmethod
    def from_json(cls, filepath: str) -> Self:
        with open(filepath, "r") as fl:
            data = json.load(fl)
        return cls(**data)


T = TypeVar("T", bound="GoogleAPIService")


class GoogleWorkspaceClient:
    """
    A client that connects to and acts as a wrapper for the Google Workspace API (v1).
    It is by no means meant to be a complete representation of the API, but rather only
    includes functionality needed for Squire.

    For an overview of the Google Workspace API, see:
    https://developers.google.com/workspace/explore
    """

    def __init__(self, settings: GoogleWorkspaceSettings):
        self._base_creds = service_account.Credentials.from_service_account_file(
            f"squire/config/{settings.service_account_token_path}", scopes=settings.scopes
        )
        self._admin = settings.directory_admin_username
        self._domain = settings.domain
        self._members_ou = settings.members_ou
        self._services: dict[str, GoogleAPIService] = {}

    def _get_service(self, cls: Type[T]) -> T:
        key = f"{cls.service_name}.{cls.version}"
        if key not in self._services:
            self._services[key] = cls(self._base_creds, self._domain, self._members_ou, self._admin)
        return cast(T, self._services[key])

    @property
    def DirectoryService(self) -> DirectoryService:
        return self._get_service(DirectoryService)
