from unittest.mock import Mock
from django.test import TestCase

from core.tests.util import suppress_warnings
from gworkspace_integration.api.formats.users import WorkspaceUser
from gworkspace_integration.api.services.directory_service import DirectoryService
from gworkspace_integration.tests.util import GoogleServiceTestMixin


class GoogleAPIDirectoryServiceTestCase(GoogleServiceTestMixin[DirectoryService], TestCase):
    """Tests for Google Workspace's Directory Service"""

    service_class = DirectoryService

    @suppress_warnings(logger_name="gworkspace_api")
    def test_get_users(self):
        """Tests whether users can be obtained, possibly paginated"""
        mock_execute: Mock = self._google_service.users.return_value.list.return_value.execute
        mock_execute.side_effect = [
            {"users": [{"id": "0"}], "nextPageToken": "next_token"},
            {"users": [{"id": "1"}]},
        ]
        users = list(self.service.users())

        self.assertEqual(mock_execute.call_count, 2)
        self.assertEqual(len(users), 2)
        for i in range(2):
            self.assertIsInstance(users[i], WorkspaceUser)
            self.assertEqual(users[i].id, str(i))

    def test_create_user(self):
        """Tests user creation"""
        mock_execute: Mock = self._google_service.users.return_value.insert.return_value.execute

        # Attempting to add a user with a domain not in the settings file should raise an error
        with self.assertRaises(ValueError):
            self.service.add_user(WorkspaceUser(id="0", primaryEmail="foo@nonconfigureddomain.com"))
        mock_execute.assert_not_called()

        # Valid domain
        self.service.add_user(WorkspaceUser(id="0", primaryEmail="foo@example.com"))
        mock_execute.assert_called_once()
