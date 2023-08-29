from django.test import TestCase

from nextcloud_integration.models import SquireNextCloudFolder
from nextcloud_integration.nextcloud_resources import NextCloudFolder
from nextcloud_integration.utils import refresh_status

from . import patch_construction


@patch_construction("utils")
class RefreshStatusTestCase(TestCase):
    fixtures = ["nextcloud_integration/nextcloud_fixtures"]

    def setUp(self):
        self.folder = SquireNextCloudFolder.objects.get(id=1)

    def test_succesful(self, mock):
        mock.return_value.exists.return_value = True
        self.assertEqual(refresh_status(self.folder), True)

    def test_fail_folder(self, mock):
        def mock_exists(resource=None):
            return not isinstance(resource, NextCloudFolder)

        mock.return_value.exists.side_effect = mock_exists

        self.assertEqual(refresh_status(self.folder), False)
        self.folder.refresh_from_db()
        self.assertEqual(self.folder.is_missing, True)
        self.assertEqual(self.folder.files.first().is_missing, False)

    def test_fail_file(self, mock):
        def mock_exists(resource=None):
            return isinstance(resource, NextCloudFolder)

        mock.return_value.exists.side_effect = mock_exists

        self.assertEqual(refresh_status(self.folder), False)
        self.folder.refresh_from_db()
        self.assertEqual(self.folder.is_missing, False)
        self.assertEqual(self.folder.files.first().is_missing, True)
