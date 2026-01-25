from datetime import datetime
import logging
from typing import Iterator

from gworkspace_integration.api.base import GoogleAPIService
from gworkspace_integration.api.formats.groups import WorkspaceGroupSettings, WorkspaceGroupMember

from googleapiclient.http import BatchHttpRequest

logger = logging.getLogger(__name__)


class GroupSettingsService(GoogleAPIService):
    """Interacting with the Group Settings API"""

    service_name = "groupssettings"
    version = "v1"

    def group_setting(self, email: str) -> Iterator[WorkspaceGroupSettings]:
        """Retrieves a group setting from the Workspace"""

        res = self._service.groups().get(groupUniqueId=email).execute()
        settings = WorkspaceGroupSettings.from_json(res)

        return settings
