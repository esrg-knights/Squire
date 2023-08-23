from django.apps import AppConfig
from django.conf import settings

from mailcow_integration.signals import register_signals as register_mailcow_signals
from mailcow_integration.squire_mailcow import SquireMailcowManager

import logging

logger = logging.getLogger(__name__)


class MailcowIntegrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mailcow_integration"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Mailcow connection
        self.mailcow_client = None

    def ready(self):
        # Setup Mailcow API client
        if settings.MAILCOW_HOST is not None:  # pragma: no cover
            logger.info(f"Mailcow client set up: {settings.MAILCOW_HOST}")
            self.mailcow_client = SquireMailcowManager(settings.MAILCOW_HOST, settings.MAILCOW_API_KEY)

            # Set up signals
            register_mailcow_signals()
        else:
            logger.warning(
                "Mailcow connection disabled. No mailcow configuration was found in the project's settings, or configuration was malformed."
            )
