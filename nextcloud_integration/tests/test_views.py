from django.contrib.auth.models import User, Permission
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.test import TestCase
from django.urls import reverse
from django.views.generic import ListView
from easywebdav.client import OperationFailed
from requests.exceptions import ConnectionError
from unittest.mock import Mock

from utils.testing.view_test_utils import ViewValidityMixin, TestMixinMixin

from nextcloud_integration.models import NCFolder
from nextcloud_integration.views import NextcloudConnectionViewMixin, FolderMixin, FileBrowserView, SiteDownloadView, \
    FolderCreateView, FolderEditView, SynchFileToFolderView, DownloadFileview

from . import patch_construction


class NextCloudConnectionMixinTestCase(TestMixinMixin, TestCase):
    mixin_class = NextcloudConnectionViewMixin

    def test_catch_connection_error(self):
        class ThrowConnectionError:
            def dispatch(self, *args, **kwargs):
                raise ConnectionError()
        response = self._build_get_response(post_inherit_class=ThrowConnectionError)
        self.assertEqual(response.status_code, 424)
        self.assertEqual(response.template_name, "nextcloud_integration/failed_nextcloud_link.html")
        self.assertIsInstance(response.context_data['error'], ConnectionError)

    def test_catch_operation_failed(self):
        class ThrowConnectionError:
            def dispatch(self, *args, **kwargs):
                # OperationFailed requires these parameters upon initiation
                raise OperationFailed(
                    method="GET",
                    path="/",
                    expected_code=200,
                    actual_code=404
                )
        response = self._build_get_response(post_inherit_class=ThrowConnectionError)
        self.assertEqual(response.status_code, 424)
        self.assertEqual(response.template_name, "nextcloud_integration/failed_nextcloud_link.html")
        self.assertIsInstance(response.context_data['error'], OperationFailed)

    @patch_construction('views')  # Replace the method in views as this is where it is imported from in memory
    def test_client_property(self, mock_client: Mock):
        self._build_get_response(save_view=True)
        self.view.client
        mock_client.assert_called()

    def test_normal_functioning(self):
        response = self._build_get_response()
        self.assertResponseSuccessful(response)


@patch_construction('views')
class FileBrowserViewTestCase(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'nextcloud_integration/nextcloud_fixtures']
    base_user_id = 100

    def setUp(self):
        super(FileBrowserViewTestCase, self).setUp()
        self.user.user_permissions.add(Permission.objects.get(codename='view_ncfolder'))

    def get_base_url(self, **url_kwargs):
        return reverse('nextcloud:browse_nextcloud', kwargs=url_kwargs)

    def test_successful_get(self, mock):
        response = self.assertValidGetResponse(url=self.get_base_url(path='plain/'))
        self.assertEqual(response.context['path'], 'plain/')
        self.assertEqual(len(response.context['nextcloud_resources']), 6)  # See mock_ls for the list

    def test_fixed_values(self, mock):
        self.assertTrue(issubclass(FileBrowserView, ListView))
        self.assertEqual(FileBrowserView.template_name, "nextcloud_integration/browser.html")

        self.assertTrue(issubclass(FileBrowserView, NextcloudConnectionViewMixin))
        self.assertTrue(issubclass(FileBrowserView, PermissionRequiredMixin))
        self.assertEqual(FileBrowserView.permission_required, 'nextcloud_integration.view_ncfolder')


class SiteDownloadViewTestCase(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'nextcloud_integration/nextcloud_fixtures']
    base_user_id = 100

    def get_base_url(self):
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


class FolderMixinTestCase(TestMixinMixin, TestCase):
    fixtures = ['nextcloud_integration/nextcloud_fixtures']
    mixin_class = FolderMixin

    def test_throw_404(self):
        self.assertRaises404(url_kwargs={'folder_slug': "nonexistent"})

    def test_folder_storage(self):
        self._build_get_response(url_kwargs={'folder_slug': "initial_folder"}, save_view=True)
        folder = NCFolder.objects.get(id=1)
        self.assertEqual(self.view.folder, folder)
        self.assertEqual(self.view.get_context_data()['folder'], folder)
