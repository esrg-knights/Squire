import logging
import os
from typing import cast

from django.apps import apps
from django.conf import settings as dj_settings

from committees.email import get_email_settings
from committees.models import AssociationGroup
from gworkspace_integration.api.client import GoogleWorkspaceClient, GoogleWorkspaceSettings
from gworkspace_integration.api.formats.groups import (
    WorkspaceGroupContactPermissions,
    WorkspaceGroupDefaultSender,
    WorkspaceGroupDiscoverPermissions,
    WorkspaceGroupJoinPermissions,
    WorkspaceGroupLeavePermissions,
    WorkspaceGroupModerationPermissions,
    WorkspaceGroupPostPermissions,
    WorkspaceGroupReplyTo,
    WorkspaceGroupSettings,
    WorkspaceGroupViewPermissions,
    WorkspaceGroupViewPermissionsExt,
)
from gworkspace_integration.apps import GworkspaceIntegrationConfig
from gworkspace_integration.workspace_manager.services.groups import SquireWorkspaceGroupService
from gworkspace_integration.workspace_manager.services.users import SquireWorkspaceUserService


def get_workspace_manager() -> "SquireGoogleWorkspaceManager | None":
    """Access the AppConfig to obtain Squire's Google Workspace Manager that connects to the Google Workspace API."""
    return cast(GworkspaceIntegrationConfig, apps.get_app_config("gworkspace_integration")).workspace_client


class SquireGoogleWorkspaceManager:
    """
    All interactions Squire makes with the Google Workspace API are handled through this class.
    It is responsible for adding members' emails to a group of member aliases (depending
    on their stored preferences), and adding members' emails to the aliases of committees
    they are in.

    Utilises caching to prevent subsequent API calls from fetching the same data.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"squire_gworkspace")
        path = os.path.join(dj_settings.CONFIG_PATH, "gworkspaceconfig.json")
        try:
            self.settings = GoogleWorkspaceSettings.from_json(path)
            self.logger.info(f"Loaded Google Workspace config from {path}")
        except FileNotFoundError:
            self.settings = None
            self.logger.warning(f"Google Workspace connection disabled. No workspace configuration found at {path}")
            return

        self._client = GoogleWorkspaceClient(self.settings)
        self._email_mgr = get_email_settings()
        if self._email_mgr is None:
            self._email_mgr = None
            self.logger.warning(f"Google Workspace connection disabled. Email settings missing!")
            return

        self.user_service = SquireWorkspaceUserService(self._client.DirectoryService, self.settings)
        self.group_service = SquireWorkspaceGroupService(
            self._client.DirectoryService, self.settings, self.user_service
        )

    @property
    def is_valid(self):
        return self.settings is not None and self._email_mgr is not None
