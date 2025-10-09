from datetime import datetime
from typing import Generator, Iterator
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

from gworkspace_integration.api.formats import WorkspaceUser


class GoogleAPIService:
    """TODO"""

    service_name: str = ""
    version: str = ""
    is_admin = False

    def __init__(self, creds: Credentials, domain: str, admin_username: str = ""):
        if self.is_admin:
            assert admin_username != ""
            creds = creds.with_subject(admin_username)
        self._domain = domain
        self._service = build(self.service_name, self.version, credentials=creds)


class DirectoryService(GoogleAPIService):
    """Interacting with the directory API"""

    service_name = "admin"
    version = "directory_v1"
    is_admin = True

    def add_user(self, user: WorkspaceUser):
        """Adds a user to the workspace"""
        if not user.primaryEmail.endswith(self._domain):
            raise ValueError(
                f"Attempting to add user to invalid domain. Expected <{self._domain}> but got <{user.primaryEmail}>"
            )
        data = {
            "primaryEmail": user.primaryEmail,
            "password": user.password,
            "hashFunction": user.hashFunction,
            "name": {
                "familyName": user.name.familyName,
                "givenName": user.name.givenName,
            },
            "archived": user.archived,
            "changePasswordAtNextLogin": user.changePasswordAtNextLogin,
            "creationTime": datetime.now().isoformat(),
            "includeInGlobalAddressList": user.includeInGlobalAddressList,
            "recoveryEmail": user.recoveryEmail,
            "suspended": user.suspended,
        }

        x = self._service.users().insert(body=data).execute()
        print(x)

    def users(self) -> Iterator[WorkspaceUser]:
        """Retrieves all users from the Workspace"""
        users = []
        page_token = ""
        extra = {}
        while True:
            results = (
                self._service.users()
                .list(customer="my_customer", **extra, query="orgUnitPath/Members", domain=self._domain)
                .execute()
            )
            users += results.get("users", [])
            page_token = results.get("nextPageToken")
            # If there's no page left, return results
            if not page_token:
                return filter(None, map(lambda u: WorkspaceUser.from_json(u), users))
            extra = {"pageToken": page_token}
