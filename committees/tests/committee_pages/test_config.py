from django.test import TestCase
from unittest.mock import Mock, patch

from utils.testing import return_boolean

from committees.committeecollective import CommitteeBaseConfig
from committees.committee_pages.config import AssociationGroupHomeConfig, AssociationGroupSettingsConfig
from committees.committeecollective import registry


class AssociationGroupHomeConfigTestCase(TestCase):
    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupHomeConfig, CommitteeBaseConfig))
        self.assertEqual(AssociationGroupHomeConfig.name, "Home")
        self.assertEqual(AssociationGroupHomeConfig.url_keyword, None)
        self.assertEqual(AssociationGroupHomeConfig.url_name, "group_general")

    def test_tab_order(self):
        """Tests that this config is first in the tab order"""
        self.assertIsInstance(registry.configs[0], AssociationGroupHomeConfig)

    @patch("committees.committee_pages.config.AssociationGroupDetailView")
    def test_home_view(self, view_mock):
        custom_view_mock = Mock(name="TestMock")
        config = AssociationGroupHomeConfig(registry=registry)
        config._home_page_filters = {}  # Reset config to prevent conflicts with registrations

        with patch("committees.committee_pages.config.AssociationGroupHomeConfig._get_filters") as filter_mock:
            filter_mock.return_value = [
                (return_boolean(False), custom_view_mock),
                (return_boolean(False), custom_view_mock),
            ]
            response = config.get_home_view(request=None, group_id=None)
            self.assertIn("AssociationGroupDetailView", response._extract_mock_name())

        with patch("committees.committee_pages.config.AssociationGroupHomeConfig._get_filters") as filter_mock:
            filter_mock.return_value = [
                (return_boolean(False), custom_view_mock),
                (return_boolean(True), custom_view_mock),
            ]
            response = config.get_home_view(request=None, group_id=None)
            self.assertIn("TestMock", response._extract_mock_name())

        # home_view = AssociationGroupHomeConfig().get_home_view()


class AssociationGroupSettingsConfigTestCase(TestCase):
    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupSettingsConfig, CommitteeBaseConfig))
        self.assertEqual(AssociationGroupSettingsConfig.name, "Settings")
        self.assertEqual(AssociationGroupSettingsConfig.url_keyword, "settings")
        self.assertEqual(AssociationGroupSettingsConfig.url_name, "settings:settings_home")

    def test_tab_order(self):
        """Tests that this config is last in the tab order"""
        self.assertIsInstance(registry.configs[-1], AssociationGroupSettingsConfig)
