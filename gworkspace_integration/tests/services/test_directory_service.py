from django.test import TestCase

from gworkspace_integration.api.services.directory_service import DirectoryService
from gworkspace_integration.tests.util import GoogleServiceTestMixin


class GoogleAPIDirectoryServiceTestCase(GoogleServiceTestMixin, TestCase):
    """Tests for Google Workspace's Directory Service"""

    service_class = DirectoryService
