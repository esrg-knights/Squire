from django.test import TestCase

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
        """ Tests that this config is first in the tab order """
        self.assertIsInstance(registry.configs[0], AssociationGroupHomeConfig)


class AssociationGroupSettingsConfigTestCase(TestCase):

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupSettingsConfig, CommitteeBaseConfig))
        self.assertEqual(AssociationGroupSettingsConfig.name, "Settings")
        self.assertEqual(AssociationGroupSettingsConfig.url_keyword, "settings")
        self.assertEqual(AssociationGroupSettingsConfig.url_name, "settings_home")

    def test_tab_order(self):
        """ Tests that this config is last in the tab order """
        self.assertIsInstance(registry.configs[0], AssociationGroupHomeConfig)
