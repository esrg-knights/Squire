from django.core.management.base import BaseCommand, CommandError

from discord_integration.views import DiscordSettings


class Command(BaseCommand):
    help = "Registers Squire's Metadata to Discord for the purposes of Linked Roles. This only needs to be run once."

    def handle(self, *args, **options):
        client = DiscordSettings.get_client()
        res = client.register_metadata()

        self.stdout.write(
            self.style.SUCCESS('Successfully registered metadata!')
        )
        self.stdout.write(str(res))
