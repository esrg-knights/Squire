import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class GworkspaceIntegrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gworkspace_integration"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Google Workspace connection
        self.workspace_client = None

    def ready(self):
        from gworkspace_integration.workspace import SquireGoogleWorkspaceManager

        try:
            # Setup Workspace API client
            self.workspace_client = SquireGoogleWorkspaceManager()
        except FileNotFoundError:
            logger.warning(
                "Google Workspace connection disabled. No workspace configuration found at squire/config/gworkspaceconfig.json."
            )
