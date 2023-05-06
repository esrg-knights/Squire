from django.test import TestCase, override_settings
from django.template import Engine

from mailing.sites import DefaultSite


class DefaultSiteTestCase(TestCase):

    @override_settings(SITE_NAME="MySite")
    def test_name(self):
        self.assertEqual(DefaultSite().name, "MySite")

    @override_settings(SITE_DOMAIN="mysite.com")
    def test_name(self):
        self.assertEqual(DefaultSite().domain, "mysite.com")
