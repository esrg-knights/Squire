from django.test import TestCase

from committees.committeecollective import CommitteeBaseConfig

from nextcloud_integration.committee_pages.config import NextcloudGroupConfig


class NextcloudGroupConfigTestCase(TestCase):
    def test_class(self):
        self.assertTrue(issubclass(NextcloudGroupConfig, CommitteeBaseConfig))
        self.assertEqual(NextcloudGroupConfig.url_keyword, "cloud")
        self.assertEqual(NextcloudGroupConfig.url_name, "nextcloud:cloud_overview")
        self.assertEqual(NextcloudGroupConfig.namespace, "nextcloud")
        self.assertEqual(
            NextcloudGroupConfig.group_requires_permission, "nextcloud_integration.change_squirenextcloudfolder"
        )
