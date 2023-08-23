from django.contrib.auth.models import User, Permission
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.test import TestCase
from django.urls import reverse
from django.views.generic import ListView, FormView
from easywebdav.client import OperationFailed
from requests.exceptions import ConnectionError
from requests.models import Response
from unittest.mock import Mock, patch

from core.tests.util import suppress_warnings
from utils.testing.view_test_utils import ViewValidityMixin, TestMixinMixin
from membership_file.util import user_is_current_member

from nextcloud_integration.forms import *
from nextcloud_integration.models import SquireNextCloudFolder, SquireNextCloudFile
from nextcloud_integration.nextcloud_resources import NextCloudFolder, NextCloudFile
from nextcloud_integration.views import (
    NextcloudConnectionViewMixin,
    FolderMixin,
    FileBrowserView,
    SiteDownloadView,
    FolderCreateView,
    FolderEditView,
    SyncFileToFolderView,
    DownloadFileview,
)

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
        self.assertIsInstance(response.context_data["error"], ConnectionError)

    def test_catch_operation_failed(self):
        class ThrowConnectionError:
            def dispatch(self, *args, **kwargs):
                # OperationFailed requires these parameters upon initiation
                raise OperationFailed(method="GET", path="/", expected_code=200, actual_code=404)

        response = self._build_get_response(post_inherit_class=ThrowConnectionError)
        self.assertEqual(response.status_code, 424)
        self.assertEqual(response.template_name, "nextcloud_integration/failed_nextcloud_link.html")
        self.assertIsInstance(response.context_data["error"], OperationFailed)

    @patch_construction("views")  # Replace the method in views as this is where it is imported from in memory
    def test_client_property(self, mock_client: Mock):
        self._build_get_response(save_view=True)
        self.view.client
        mock_client.assert_called()

    def test_normal_functioning(self):
        response = self._build_get_response()
        self.assertResponseSuccessful(response)


@patch_construction("views")
class FileBrowserViewTestCase(ViewValidityMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "nextcloud_integration/nextcloud_fixtures"]
    permission_required = "nextcloud_integration.view_squirenextcloudfolder"
    base_user_id = 100

    def setUp(self):
        super(FileBrowserViewTestCase, self).setUp()
        self.user.user_permissions.add(Permission.objects.get(codename="view_squirenextcloudfolder"))

    def get_base_url(self, **url_kwargs):
        return reverse("nextcloud:browse_nextcloud", kwargs=url_kwargs)

    def test_successful_get(self, mock: Mock):
        response = self.assertValidGetResponse(url=self.get_base_url(path="plain/"))
        self.assertEqual(response.context["path"], "plain/")
        self.assertEqual(len(response.context["nextcloud_resources"]), 6)  # See mock_ls for the list

    def test_fixed_values(self, mock: Mock):
        self.assertTrue(issubclass(FileBrowserView, ListView))
        self.assertEqual(FileBrowserView.template_name, "nextcloud_integration/browser.html")

        self.assertTrue(issubclass(FileBrowserView, NextcloudConnectionViewMixin))
        self.assertTrue(issubclass(FileBrowserView, PermissionRequiredMixin))
        self.assertEqual(FileBrowserView.permission_required, "nextcloud_integration.view_squirenextcloudfolder")

    def test_path_not_existent(self, mock: Mock):
        # When the path is not existent, a different layout is returned
        def throw_error(path="/", **kwargs):
            raise OperationFailed(method="GET", path=path, expected_code=200, actual_code=404)

        mock.return_value.ls.side_effect = throw_error
        response = self.assertValidGetResponse(url=self.get_base_url(path="does-not-exist/"))
        self.assertEqual(response.template_name, "nextcloud_integration/browser_not_exist.html")
        self.assertEqual(response.context["path"], "does-not-exist/")

    def test_requires_permission(self, mock: Mock):
        self.assertRequiresPermission()


class SiteDownloadViewTestCase(ViewValidityMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "nextcloud_integration/nextcloud_fixtures"]
    base_user_id = 100

    def get_base_url(self):
        return reverse("nextcloud:site_downloads")

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_template_context(self):
        response = self.client.get(self.get_base_url(), data={})
        context = response.context

        self.assertIn(SquireNextCloudFolder.objects.get(id=1), context["folders"])

    def test_not_on_overview_page(self):
        response = self.client.get(self.get_base_url(), data={})
        context = response.context

        self.assertNotIn(SquireNextCloudFolder.objects.get(id=3), context["folders"])

    def test_member_access(self):
        response = self.client.get(self.get_base_url(), data={})
        context = response.context

        self.assertIn(SquireNextCloudFolder.objects.get(id=2), context["folders"])
        self.assertIn(SquireNextCloudFolder.objects.get(id=1), context["folders"])

    def test_non_member_access(self):
        self.user = User.objects.get(id=2)
        self.client.force_login(self.user)

        response = self.client.get(self.get_base_url(), data={})
        context = response.context

        self.assertNotIn(
            SquireNextCloudFolder.objects.get(id=2), context["folders"]
        )  # Id 2 has no required membership
        self.assertIn(SquireNextCloudFolder.objects.get(id=1), context["folders"])

    def test_user_not_logged_in_message(self):
        self.client.logout()
        response = self.assertValidGetResponse()
        unique_message = response.context["unique_messages"][0]
        self.assertIsNotNone(unique_message)
        self.assertTrue(unique_message["msg_text"].find("not logged in") >= 0)
        self.assertEqual(unique_message["msg_type"], "warning")
        self.assertEqual(unique_message["btn_text"], "Log in!")
        self.assertEqual(unique_message["btn_url"], reverse("core:user_accounts/login"))

    def test_user_is_not_member(self):
        user = User.objects.get(id=1)
        self.client.force_login(user)
        response = self.assertValidGetResponse()
        unique_message = response.context["unique_messages"][0]
        self.assertIsNotNone(unique_message)
        self.assertTrue(unique_message["msg_text"].find("not a member") >= 0)
        self.assertEqual(unique_message["msg_type"], "warning")


class FolderMixinTestCase(TestMixinMixin, TestCase):
    fixtures = ["nextcloud_integration/nextcloud_fixtures"]
    mixin_class = FolderMixin

    def test_throw_404(self):
        self.assertRaises404(url_kwargs={"folder_slug": "nonexistent"})

    def test_folder_storage(self):
        self._build_get_response(url_kwargs={"folder_slug": "initial_folder"}, save_view=True)
        folder = SquireNextCloudFolder.objects.get(id=1)
        self.assertEqual(self.view.folder, folder)
        self.assertEqual(self.view.get_context_data()["folder"], folder)


@patch_construction("forms")
class FolderCreateViewTestCase(ViewValidityMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "nextcloud_integration/nextcloud_fixtures"]
    permission_required = "nextcloud_integration.add_squirenextcloudfolder"
    base_user_id = 100

    def get_base_url(self):
        return reverse("nextcloud:add_folder")

    def test_fixed_values(self, mock):
        self.assertTrue(issubclass(FolderCreateView, NextcloudConnectionViewMixin))
        self.assertTrue(issubclass(FolderCreateView, FormView))
        self.assertEqual(FolderCreateView.form_class, FolderCreateForm)
        self.assertEqual(FolderCreateView.template_name, "nextcloud_integration/folder_add.html")

    def test_successful_get(self, mock):
        self.assertValidGetResponse()

    def test_succesful_post(self, mock):
        self.assertValidPostResponse(
            data={
                "display_name": "FolderCreateView TestFolder",
                "description": "random description",
            },
            redirect_url=reverse("nextcloud:site_downloads"),
        )
        # Ensure folder creation
        self.assertTrue(SquireNextCloudFolder.objects.filter(display_name="FolderCreateView TestFolder").exists())

    def test_requires_permission(self, mock):
        self.assertRequiresPermission()


class FolderEditViewTestCase(ViewValidityMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "nextcloud_integration/nextcloud_fixtures"]
    permission_required = "nextcloud_integration.change_squirenextcloudfolder"
    base_user_id = 100

    def get_base_url(self):
        return reverse("nextcloud:folder_edit", kwargs={"folder_slug": "initial_folder"})

    def test_fixed_values(self):
        self.assertTrue(issubclass(FolderEditView, NextcloudConnectionViewMixin))
        self.assertTrue(issubclass(FolderEditView, FolderMixin))
        self.assertTrue(issubclass(FolderEditView, FormView))
        self.assertEqual(FolderEditView.form_class, FolderEditFormGroup)
        self.assertEqual(FolderEditView.template_name, "nextcloud_integration/folder_edit.html")

    def test_successful_get(self):
        self.assertValidGetResponse()

    @patch("nextcloud_integration.views.FolderEditFormGroup.save")
    def test_succesful_post(self, mock):
        self.assertValidPostResponse(
            data={
                "main-display_name": "Initial folder",
                "main-description": "initial folder adjustments",
                "formset-TOTAL_FORMS": 2,
                "formset-INITIAL_FORMS": 0,
                "formset-MIN_NUM_FORMS": 0,
                "formset-MAX_NUM_FORMS": 2,
                "formset-0-display_name": "Item 1",
                "formset-0-description": "description 1",
                "formset-1-display_name": "Item 2",
                "formset-1-description": "description 2",
            },
            redirect_url=reverse("nextcloud:site_downloads"),
        )
        mock.assert_called()

    def test_requires_permission(self):
        self.assertRequiresPermission()


@patch_construction("forms")
class SyncFileToFolderViewTestCase(ViewValidityMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "nextcloud_integration/nextcloud_fixtures"]
    permission_required = "nextcloud_integration.sync_squirenextcloudfile"
    base_user_id = 100

    def get_base_url(self):
        return reverse("nextcloud:sync_file", kwargs={"folder_slug": "initial_folder"})

    def test_fixed_values(self, mock):
        self.assertTrue(issubclass(SyncFileToFolderView, NextcloudConnectionViewMixin))
        self.assertTrue(issubclass(SyncFileToFolderView, FolderMixin))
        self.assertTrue(issubclass(SyncFileToFolderView, FormView))
        self.assertEqual(SyncFileToFolderView.form_class, SyncFileToFolderForm)
        self.assertEqual(SyncFileToFolderView.template_name, "nextcloud_integration/sync_file_to_folder.html")

    def test_successful_get(self, mock):
        self.assertValidGetResponse()

    def test_requires_permission(self, mock):
        self.assertRequiresPermission()

    @patch("nextcloud_integration.forms.SyncFileToFolderForm.save")
    def test_succesful_post(self, mock_save, mock_construct_client):
        self.assertValidPostResponse(
            data={
                "display_name": "New Synced File",
                "description": "Test file that does not actually exist",
                "selected_file": "new_file.txt",
            },
            redirect_url=reverse("nextcloud:site_downloads"),
        )
        mock_save.assert_called()


@patch_construction("views")
class DownloadFileViewTestCase(ViewValidityMixin, TestCase):
    fixtures = ["test_users", "test_members", "nextcloud_integration/nextcloud_fixtures"]
    base_user_id = 100

    def setUp(self):
        self.file = SquireNextCloudFile.objects.get(id=1)
        super(DownloadFileViewTestCase, self).setUp()

    def mock_download(self, mock):
        file_path = f"nextcloud_integration/tests/files/test_download_file.txt"

        def fake_download(nc_file=None):
            resp = Response()
            with open(file_path, "r") as file:
                resp._content = file.read()
            resp.status_code = 200
            resp.cookies = {"fake_cookie": "this_should_not_be_shared"}

            return resp

        mock.return_value.download.side_effect = fake_download

    def get_base_url(self, file=None):
        if file is None:
            file = self.file
        return reverse("nextcloud:file_dl", kwargs={"folder_slug": file.folder.slug, "file_slug": file.slug})

    def test_fixed_values(self, mock):
        self.assertTrue(issubclass(DownloadFileview, NextcloudConnectionViewMixin))
        self.assertEqual(DownloadFileview.template_name, "nextcloud_integration/file_download_test.html")
        self.assertEqual(DownloadFileview.http_method_names, ["get"])

    def test_successful_get(self, mock):
        self.mock_download(mock)
        self.assertValidGetResponse()

    @suppress_warnings()
    def test_file_not_found(self, mock):
        response = self.client.get(
            reverse("nextcloud:file_dl", kwargs={"folder_slug": "initial_folder", "file_slug": "fake_file"})
        )
        self.assertEqual(response.status_code, 404)

    def test_members_only_access(self, mock):
        self.mock_download(mock)

        nc_file = SquireNextCloudFile.objects.filter(folder__requires_membership=True).first()

        self.assertTrue(user_is_current_member(self.user))
        self.assertValidGetResponse(url=self.get_base_url(nc_file))

        self.user = User.objects.get(id=1)
        self.assertFalse(user_is_current_member(self.user))
        self.client.force_login(self.user)
        self.assertPermissionDenied(url=self.get_base_url(nc_file))

    @staticmethod
    def fail_download(*args, actual_code=404, **kwargs):
        raise OperationFailed(method="GET", path="/", expected_code=200, actual_code=actual_code)

    def test_disconnected_file(self, mock):
        """Test that a download failing due to a disconnected file adjusts database state"""
        self.assertEqual(self.file.is_missing, False)
        # Ensure that an exception is created
        mock.return_value.download.side_effect = self.fail_download

        # Adjust the exist method
        def exists(resource=None):
            if isinstance(resource, NextCloudFile):
                return False
            return True

        mock.return_value.exists.side_effect = exists

        response = self.client.get(self.get_base_url(), follow=True)
        self.file.refresh_from_db()
        self.assertEqual(self.file.is_missing, True)
        self.assertHasMessage(response, 40, "The file could not be retrieved")
        self.assertEqual(response.request["PATH_INFO"], reverse("nextcloud:site_downloads"))

    def test_disconnected_folder(self, mock):
        """Test that a download failing due to disconnected folder adjusts database state"""
        self.assertEqual(self.file.folder.is_missing, False)
        # Ensure that an exception is created
        mock.return_value.download.side_effect = self.fail_download

        # Adjust the exist method
        def exists(resource=None):
            if isinstance(resource, NextCloudFolder):
                return False
            return True

        mock.return_value.exists.side_effect = exists

        response = self.client.get(self.get_base_url(), follow=True)
        self.file.folder.refresh_from_db()
        self.assertEqual(self.file.folder.is_missing, True)
        self.assertHasMessage(response, 40, "The file could not be retrieved as its folder has been moved or renamed")
        self.assertEqual(response.request["PATH_INFO"], reverse("nextcloud:site_downloads"))

    def test_nextcloud_error(self, mock):
        """Test that a download failing due to connection error raises an error"""
        # Ensure that an exception is created
        mock.return_value.download.side_effect = self.fail_download
        response = self.client.get(self.get_base_url(), follow=True)
        self.assertHasMessage(response, 40)
        self.assertEqual(response.request["PATH_INFO"], reverse("nextcloud:site_downloads"))

    def test_missing_file(self, mock):
        """Test that a download on a missing file is not initiated"""
        self.file.is_missing = True
        self.file.save()
        response = self.client.get(self.get_base_url(), follow=True)
        self.assertHasMessage(response, "ERROR", "File could not be retrieved")
        self.assertEqual(response.request["PATH_INFO"], reverse("nextcloud:site_downloads"))

    def test_missing_folder(self, mock):
        """Test that a download on a missing file is not initiated"""
        self.file.folder.is_missing = True
        self.file.folder.save()
        response = self.client.get(self.get_base_url(), follow=True)
        self.assertHasMessage(response, "ERROR", "File could not be retrieved")
        self.assertEqual(response.request["PATH_INFO"], reverse("nextcloud:site_downloads"))
