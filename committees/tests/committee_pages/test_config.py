from django.test import TestCase

from committees.committeecollective import CommitteeBaseConfig
from committees.committee_pages.config import AssociationGroupWelcomeConfig

from committees.committeecollective import registry


class AssociationGroupHomeConfigTestCase(TestCase):

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupWelcomeConfig, CommitteeBaseConfig))
        self.assertEqual(AssociationGroupWelcomeConfig.url_keyword, "main")
        self.assertEqual(AssociationGroupWelcomeConfig.url_name, "group_general")

    def test_tab_order(self):
        """ Tests that this config is first in the tab order """
        self.assertIsInstance(registry.configs[0], AssociationGroupWelcomeConfig)
