from django.test import TestCase


from committees.committeecollective import get_all_configs, CommitteeConfig


def test_get_all_configs(self):
    configs = get_all_configs()
    for config in configs:
        self.assertIsInstance(config, CommitteeConfig)


class FakeConfig(CommitteeConfig):
    name = 'test_config'
    tab_select_keyword = 'tab_test'
    url_name = ''
    namespace = 'test_namespace'

    def get_urls(self):
        # An empty list to prevent the not implemented error
        return []


class TestCommitteeConfig(TestCase):

    def setUp(self):
        self.config = FakeConfig()

    def test_urls(self):
        urls = self.config.urls
        self.assertEqual(set([]), set(urls[0]))
        self.assertEqual(urls[1], self.config.namespace)
        self.assertEqual(urls[2], self.config.namespace)
