from django.test import TestCase

from committees.committeecollective import CommitteeBaseConfig
from committees.committee_pages.config import AssociationGroupHomeConfig

from committees.committeecollective import registry


class AssociationGroupHomeConfigTestCase(TestCase):

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupHomeConfig, CommitteeBaseConfig))
        self.assertEqual(AssociationGroupHomeConfig.url_keyword, "main")
        self.assertEqual(AssociationGroupHomeConfig.url_name, "group_general")

    def test_tab_order(self):
        """ Tests that this config is first in the tab order """
        self.assertIsInstance(registry.configs[0], AssociationGroupHomeConfig)
