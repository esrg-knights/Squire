from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from mailcow_integration.api.client import MailcowAPIClient
from mailcow_integration.api.interface.mailbox import MailcowMailbox

class Command(BaseCommand): # pragma: no cover
    help = 'Quick testing for the Mailcow client. Useful for development and debugging, but should not be used in production.'

    def add_arguments(self, parser):
        parser.add_argument('endpoint', type=str)

    def handle(self, *args, **options):
        # Mailcow API cannot handle ipv6. This hack forces usage of ipv4
        import requests
        requests.packages.urllib3.util.connection.HAS_IPV6 = False

        # NOTE: The Mailcow API uses an IP whitelist. Make sure to add your local IP to this list in the admin panel.
        client = MailcowAPIClient(settings.MAILCOW_HOST, settings.MAILCOW_API_KEY)

        res = client._make_request(options['endpoint'])

        self.stdout.write(self.style.SUCCESS(res))
        self.stdout.write(self.style.SUCCESS(res.content))
