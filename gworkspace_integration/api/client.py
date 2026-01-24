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
    - `primary_domain`: Main domain of the Workspace
    - `domains`: Domains set up in the Workspace.
    - `members_ou`: Organizational unit to sync Squire's members to. Users in other OU's are outside the scope of Squire.
    - `directory_admin_username`: Username of an admin account. This is required to use the directory API to manage users/groups
    """

    service_account_token_path: str
    primary_domain: str
    domains: str
    customer_id: str
    members_ou: str
    directory_admin_username: str
    scopes: list[str]

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
        self.admin_username = settings.directory_admin_username
        self.domain = settings.primary_domain
        self.workspace_domains = settings.domains
        self.members_ou = settings.members_ou
        self._services: dict[str, GoogleAPIService] = {}

    def _get_service(self, cls: Type[T]) -> T:
        key = f"{cls.service_name}.{cls.version}"
        if key not in self._services:
            self._services[key] = cls(self._base_creds, self.domain, self.members_ou, self.admin_username)
        return cast(T, self._services[key])

    @property
    def DirectoryService(self) -> DirectoryService:
        return self._get_service(DirectoryService)
