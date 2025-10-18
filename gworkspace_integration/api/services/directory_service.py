from datetime import datetime
import logging
from typing import Iterator

from gworkspace_integration.api.base import GoogleAPIService
from gworkspace_integration.api.formats.users import WorkspaceUser
from gworkspace_integration.api.formats.groups import WorkspaceGroup


logger = logging.getLogger(__name__)


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
            "externalIds": [
                {
                    "type": eid.type,
                    "value": eid.value,
                    **({"customType": eid.customType} if eid.type == "custom" else {}),
                }
                for eid in user.external_ids
            ],
        }

        # Returns JSON of newly created user
        x = self._service.users().insert(body=data).execute()
        print(x)

    def users(self) -> Iterator[WorkspaceUser]:
        """Retrieves all users from the Workspace"""
        users = []
        page_token = ""
        extra: dict[str, str] = {}
        for _ in range(10):
            results = (
                self._service.users()
                .list(customer="my_customer", **extra, query=f"orgUnitPath={self._members_ou}", domain=self._domain)
                .execute()
            )
            users += results.get("users", [])
            page_token = results.get("nextPageToken")
            # If there's no page left, return results
            if not page_token:
                break
            extra = {"pageToken": page_token}

        if page_token:  # pragma: no cover
            # Shouldn't happen
            logger.error(
                f"More than 10 pages of users returned when fetching from the Directory API. {len(users)} users returned."
            )
        return filter(None, map(lambda u: WorkspaceUser.from_json(u), users))

    def groups(self):
        """Retrieve all groups from the workspace"""
        groups = []
        page_token = ""
        extra: dict[str, str] = {}
        for _ in range(10):
            results = self._service.groups().list(customer="my_customer", **extra, domain=self._domain).execute()
            groups += results.get("groups", [])
            page_token = results.get("nextPageToken")
            # If there's no page left, return results
            if not page_token:
                break
            extra = {"pageToken": page_token}

        if page_token:  # pragma: no cover
            # Shouldn't happen
            logger.error(
                f"More than 10 pages of users returned when fetching from the Directory API. {len(groups)} users returned."
            )
        return filter(None, map(lambda g: WorkspaceGroup.from_json(g), groups))
