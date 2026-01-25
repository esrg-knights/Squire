from json import JSONDecodeError

from django.core.management.base import BaseCommand
from google.auth.exceptions import MalformedError, RefreshError
from google.auth.transport.requests import Request

from gworkspace_integration.api.client import GoogleWorkspaceClient, GoogleWorkspaceSettings


class Command(BaseCommand):  # pragma: no cover
    help = "Verify the validity of the Google Workspace token and related settings."

    def handle(self, *args, **options):
        # Check settings file validity
        try:
            settings = GoogleWorkspaceSettings.from_json("squire/config/gworkspaceconfig.json")
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR("Google Workspace configuration not found at squire/config/gworkspaceconfig.json")
            )
            return
        except JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Could not parse JSON squire/config/gworkspaceconfig.json: {e}"))
            return
        self.stdout.write(self.style.SUCCESS("Correctly parsed squire/config/gworkspaceconfig.json"))

        # Check token validity
        try:
            client = GoogleWorkspaceClient(settings)
            client._base_creds.refresh(Request())
        except FileNotFoundError as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Could not locate service account token at squire/config/{settings.service_account_token_path}"
                )
            )
            return
        except MalformedError as e:
            self.stdout.write(self.style.ERROR(f"Service token is malformed: {e}"))
            return
        except RefreshError as e:
            self.stdout.write(self.style.ERROR(f"Service token is invalid (RefreshError): {e}"))
            return
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Unknown error when parsing service token: {e.__module__}.{e.__class__.__qualname__}: {e}"
                )
            )
            return
        self.stdout.write(self.style.SUCCESS("Correctly parsed service account token!"))

        # Check admin validity (needed to use directory API to manage users/groups)
        try:
            client.DirectoryService._service.users().list(customer="my_customer", maxResults=1).execute()
        except RefreshError as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Admin username ({settings.directory_admin_username}) is invalid or does not have sufficient permissions: {e}"
                )
            )
            return
        self.stdout.write(self.style.SUCCESS("Correctly utilised admin user!"))
