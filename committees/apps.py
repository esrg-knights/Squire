import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CommitteesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "committees"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.email_manager = None

    def ready(self):
        from committees.email import SquireEmailManager

        try:
            # Setup Workspace API client
            self.email_manager = SquireEmailManager()
        except FileNotFoundError:
            logger.warning("No email config configuration found at squire/config/emailconfig.json.")
