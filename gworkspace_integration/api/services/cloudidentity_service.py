from datetime import datetime
import logging
from typing import Iterator

from gworkspace_integration.api.base import GoogleAPIService
from gworkspace_integration.api.formats.users import WorkspaceUser
from gworkspace_integration.api.formats.groups import WorkpaceCloudIdentityGroup, WorkspaceGroup


logger = logging.getLogger(__name__)


class CloudIdentityService(GoogleAPIService):  # pragma: no cover
    """
    Interacting with the Cloud Identity API
    See: https://developers.google.com/workspace/explore?discoveryUrl=https%3A%2F%2Fcloudidentity.googleapis.com%2F%24discovery%2Frest%3Fversion%3Dv1
    """

    service_name = "cloudidentity"
    version = "v1"

    PLACEHOLDER_CUSTOMER_ID = "XXXXXX"

    def groups(self) -> Iterator[WorkpaceCloudIdentityGroup]:
        """Retrieve all groups from the workspace"""
        groups = []
        page_token = ""
        extra: dict[str, str] = {
            "query": f"parent=='customers/{self.PLACEHOLDER_CUSTOMER_ID}'&&domain_name=='{self._domain}'"
        }
        for _ in range(10):
            results = self._service.groups().search(**extra).execute()
            groups += results.get("groups", [])
            page_token = results.get("nextPageToken")
            # If there's no page left, return results
            if not page_token:
                break
            extra["pageToken"] = page_token

        if page_token:  # pragma: no cover
            # Shouldn't happen
            logger.error(
                f"More than 10 pages of groups returned when fetching from the Cloud Identity API. {len(groups)} groups returned."
            )
        return filter(None, map(lambda g: WorkpaceCloudIdentityGroup.from_json(g), groups))
