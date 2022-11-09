from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from utils.testing.view_test_utils import ViewValidityMixin

from nextcloud_integration.models import NCFolder


class TestSiteDownloadView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'nextcloud_integration/nextcloud_fixtures']
    base_user_id = 100

    def get_base_url(self, content_type=None, item_id=None):
        return reverse('nextcloud:site_downloads')

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_template_context(self):
        response  = self.client.get(self.get_base_url(), data={})
        context = response.context

        self.assertIn(NCFolder.objects.get(id=1), context["folders"])

    def test_not_on_overview_page(self):
        response  = self.client.get(self.get_base_url(), data={})
        context = response.context

        self.assertNotIn(NCFolder.objects.get(id=3), context["folders"])

    def test_member_access(self):
        response  = self.client.get(self.get_base_url(), data={})
        context = response.context

        self.assertIn(NCFolder.objects.get(id=2), context["folders"])
        self.assertIn(NCFolder.objects.get(id=1), context["folders"])

    def test_non_member_access(self):
        self.user = User.objects.get(id=2)
        self.client.force_login(self.user)

        response  = self.client.get(self.get_base_url(), data={})
        context = response.context

        self.assertNotIn(NCFolder.objects.get(id=2), context["folders"])  # Id 2 has no required membership
        self.assertIn(NCFolder.objects.get(id=1), context["folders"])
