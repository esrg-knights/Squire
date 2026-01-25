from datetime import datetime
import logging
from typing import Iterator

from gworkspace_integration.api.base import GoogleAPIService
from gworkspace_integration.api.formats.users import WorkspaceUser
from gworkspace_integration.api.formats.groups import WorkspaceGroup, WorkspaceGroupMember

from googleapiclient.http import BatchHttpRequest

logger = logging.getLogger(__name__)


class DirectoryService(GoogleAPIService):
    """Interacting with the directory API"""

    service_name = "admin"
    version = "directory_v1"

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
        print(f"add user res: {x}")

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

    def groups(self) -> Iterator[WorkspaceGroup]:
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

    def group_members(self, group_key: str):
        """Retrieves all members from a group"""
        members = []
        page_token = ""
        extra: dict[str, str] = {}
        for _ in range(10):
            results = self._service.members().list(groupKey=group_key, **extra).execute()
            members += results.get("members", [])
            page_token = results.get("nextPageToken")
            # If there's no page left, return results
            if not page_token:
                break
            extra = {"pageToken": page_token}

        if page_token:  # pragma: no cover
            # Shouldn't happen
            logger.error(
                f"More than 10 pages of members returned when fetching from the Directory API for group {group_key}. {len(members)} members returned."
            )
        return filter(None, map(lambda m: WorkspaceGroupMember.from_json(m), members))

    def bulk_change_group_members(
        self,
        group_key: str,
        group_members_update: list[WorkspaceGroupMember],
        group_members_add: list[WorkspaceGroupMember],
        group_members_remove: list[WorkspaceGroupMember],
    ):
        """
        Modifies a group's members in bulk. Supports additions, removals, and updates.
        """

        def response_callback(request_id, response, exception):
            if exception is not None:
                logger.error(f"Error while updating group members in bulk: {exception}.")
                return
            logger.debug(f"Batch response: {response}")
            # {
            #     "kind": "admin#directory#member",
            #     "etag": '"gpBsXqCiY3kGaDliRWSpRKSlyHGOMsQoSYVVy5SUbI8/fU3M-X6YUdHhKi0Y874EDQ7XJ-M"',
            #     "id": "104027548304300011995",
            #     "email": "test@example.com",
            #     "role": "MEMBER",
            #     "type": "USER",
            #     "status": "ACTIVE",
            #     "delivery_settings": "ALL_MAIL",
            # }

        batch = self._service.new_batch_http_request()
        for member in group_members_add:
            logger.debug(f"ADDING {member.email} to {group_key}")
            body = {
                "kind": member.kind,
                "email": member.email,
                "role": member.role.name,
                "type": member.type.name,
                "delivery_settings": member.delivery_settings.name,
            }
            batch.add(self._service.members().insert(groupKey=group_key, body=body), callback=response_callback)

        for member in group_members_remove:
            logger.debug(f"REMOVING {member.email} from {group_key}")
            assert (
                member.id is not None and member.id != ""
            ), f"member.id unexpectedly empty when deleting {member.email}"
            batch.add(
                self._service.members().delete(groupKey=group_key, memberKey=member.id), callback=response_callback
            )
        batch.execute()

        # Updating should be done in a separate batch because of etag-shenanigans. Patch requires one, while update/delete can't have one
        batch_update = self._service.new_batch_http_request()
        for member in group_members_update:
            logger.debug(f"UPDATING {member.email} in {group_key}")
            body = {
                "kind": member.kind,
                "email": member.email,
                "role": member.role.name,
                "type": member.type.name,
                "delivery_settings": member.delivery_settings.name,
            }
            assert (
                member.id is not None and member.id != ""
            ), f"member.id unexpectedly empty when updating {member.email}"
            batch_update.add(
                self._service.members().patch(groupKey=group_key, memberKey=member.id, body=body),
                callback=response_callback,
            )
        batch_update.execute()
