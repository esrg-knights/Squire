from django.conf import settings
from django.core.management.base import BaseCommand

from mailcow_integration.api.client import MailcowAPIClient


class Command(BaseCommand):  # pragma: no cover
    help = "Quick testing for the Mailcow client. Useful for development and debugging, but should not be used in production."

    def add_arguments(self, parser):
        parser.add_argument("endpoint", type=str)

    def handle(self, *args, **options):
        # NOTE: The Mailcow API uses an IP whitelist. Make sure to add your local IP to this list in the Mailcow admin panel.
        assert settings.MAILCOW_HOST is not None, "Mailcow host should be set in the settings"
        assert settings.MAILCOW_API_KEY is not None, "Mailcow API key should be set in the settings"
        client = MailcowAPIClient(settings.MAILCOW_HOST, settings.MAILCOW_API_KEY)

        res = client._make_request(options["endpoint"])

        self.stdout.write(self.style.SUCCESS(res))
        if not isinstance(res, list):
            self.stdout.write(self.style.SUCCESS(res.content))
