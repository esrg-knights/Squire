from unittest.mock import Mock, patch

from django.test import TestCase
from gworkspace_integration.api.base import GoogleAPIService
from gworkspace_integration.api.client import GoogleWorkspaceClient, GoogleWorkspaceSettings


class GoogleServiceTestMixin:
    """Mixin class that contains general tests for the various Google Services"""

    service_class: type[GoogleAPIService] = None

    @classmethod
    def setUpClass(cls):
        assert cls.service_class is not None, f"Must override service class in {cls.__qualname__}"
        return super().setUpClass()

    @patch("googleapiclient.discovery.build")
    @patch("google.oauth2.service_account.Credentials")
    def test_fetch_service(self, mock_creds: Mock, mock_build: Mock):
        """Tests whether this service can be retrieved from the client, is correctly built, and not unnecessarily built additional times."""
        mock_creds_service = mock_creds.from_service_account_file.return_value = Mock()
        mock_creds_admin = mock_creds_service.with_subject.return_value = Mock()

        settings = GoogleWorkspaceSettings(
            service_account_token_path="example.json",
            scopes=[],
            domain="example.com",
            directory_admin_username="admin@example.com",
        )
        client = GoogleWorkspaceClient(settings)

        # Instantiating doesn't build any service
        mock_creds_service.with_subject.assert_not_called()
        mock_build.assert_not_called()

        # Should have a method/property to obtain the service
        self.assertTrue(
            hasattr(client, self.service_class.__name__),
            f"Cannot obtain {self.service_class} from GoogleWorkspaceClient. Relevant method does not exist!",
        )
        instance = getattr(client, self.service_class.__name__)
        self.assertIsInstance(
            instance,
            self.service_class,
            f"Fetching GoogleWorkspaceClient.{self.service_class.__name__}(..) resulted in an invalid instance of type {instance.__class__.__name__}",
        )

        # Build should be called with the relevant credentials
        expected_creds = mock_creds_service
        if self.service_class.is_admin:
            expected_creds = mock_creds_admin
        mock_build.assert_called_once_with(
            self.service_class.service_name,
            self.service_class.version,
            credentials=expected_creds,
        )

        # Should only build admin credentials once, if required
        if self.service_class.is_admin:
            mock_creds_service.with_subject.assert_called_once_with(settings.directory_admin_username)
        else:
            mock_creds_service.with_subject.assert_not_called()

        # Should only build the service once, even if retrieved multiple times
        mock_build.reset_mock()
        getattr(client, self.service_class.__name__)
        mock_build.assert_not_called()
