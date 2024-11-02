from django.contrib import messages
from django.test import TestCase
from django.urls import reverse
from django.views.generic import TemplateView, ListView, View

from unittest.mock import patch

from committees.mixins import AssociationGroupMixin
from committees.tests.committee_pages.utils import AssocationGroupTestingMixin
from utils.testing.view_test_utils import ViewValidityMixin, TestMixinMixin

from nextcloud_integration.models import SquireNextCloudFolder
from nextcloud_integration.tests import patch_construction
from nextcloud_integration.views import (
    NextcloudConnectionViewMixin,
    FolderMixin,
    FolderCreateView,
    FolderEditView,
    SyncFileToFolderView,
)

from nextcloud_integration.committee_pages.views import *


class CloudOverviewTestCase(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "nextcloud_integration/nextcloud_fixtures"]
    group_permissions_required = "nextcloud_integration.change_squirenextcloudfolder"
    base_user_id = 100
    url_name = "nextcloud:cloud_overview"

    def test_fixed_values(self):
        self.assertTrue(issubclass(CloudFoldersOverview, AssociationGroupMixin))
        self.assertTrue(issubclass(CloudFoldersOverview, ListView))
        self.assertEqual(
            CloudFoldersOverview.template_name,
            "nextcloud_integration/committees/committee_cloud_folders_overview.html",
        )

    def test_successful_get(self):
        self.assertValidGetResponse()


@patch_construction("forms")
class CloudFolderCreateViewTestCase(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "nextcloud_integration/nextcloud_fixtures"]
    group_permissions_required = "nextcloud_integration.change_squirenextcloudfolder"
    base_user_id = 100
    url_name = "nextcloud:cloud_add_folder"

    def test_fixed_values(self, mock):
        self.assertTrue(issubclass(CloudFolderCreateView, AssociationGroupMixin))
        self.assertTrue(issubclass(CloudFolderCreateView, FolderCreateView))
        self.assertEqual(
            CloudFolderCreateView.template_name, "nextcloud_integration/committees/committee_cloud_folder_add.html"
        )

    def test_successful_get(self, mock):
        self.assertValidGetResponse()

    def test_succesful_post(self, mock):
        self.assertValidPostResponse(
            data={
                "display_name": "FolderCreateView TestFolder",
                "description": "random description",
            },
            redirect_url=reverse("committees:nextcloud:cloud_overview", kwargs={"group_id": self.association_group}),
        )


class TestFolderMixin(AssocationGroupTestingMixin, ViewValidityMixin):
    fixtures = ["test_users", "test_groups", "test_members.json", "nextcloud_integration/nextcloud_fixtures"]
    group_permissions_required = "nextcloud_integration.change_squirenextcloudfolder"
    base_user_id = 100

    def setUp(self):
        self.folder = SquireNextCloudFolder.objects.get(id=1)
        super(TestFolderMixin, self).setUp()

    def get_url_kwargs(self, **kwargs):
        return super(TestFolderMixin, self).get_url_kwargs(folder_slug=self.folder.slug, **kwargs)


class CloudFolderEditViewTestCase(TestFolderMixin, TestCase):
    url_name = "nextcloud:folder_edit"

    def test_fixed_values(self):
        self.assertTrue(issubclass(CloudFolderEditView, AssociationGroupMixin))
        self.assertTrue(issubclass(CloudFolderEditView, FolderEditView))
        self.assertEqual(
            CloudFolderEditView.template_name, "nextcloud_integration/committees/committee_cloud_folder_edit.html"
        )

    def test_successful_get(self):
        self.assertValidGetResponse()

    def test_succesful_post(self):
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
            redirect_url=reverse("committees:nextcloud:cloud_overview", kwargs={"group_id": self.association_group}),
        )


@patch_construction("forms")
class CloudFileSyncViewTestCase(TestFolderMixin, TestCase):
    url_name = "nextcloud:folder_sync_file"
    group_permissions_required = (
        "nextcloud_integration.change_squirenextcloudfolder",
        "nextcloud_integration.sync_squirenextcloudfile",
    )

    def test_fixed_values(self, mock):
        self.assertTrue(issubclass(CloudFileSyncView, AssociationGroupMixin))
        self.assertTrue(issubclass(CloudFileSyncView, SyncFileToFolderView))
        self.assertEqual(
            CloudFileSyncView.template_name, "nextcloud_integration/committees/committee_cloud_folder_sync.html"
        )

    def test_successful_get(self, mock):
        self.assertValidGetResponse()

    def test_succesful_post(self, mock):
        self.assertValidPostResponse(
            data={
                "display_name": "New Synced File",
                "description": "Test file that does not actually exist",
                "selected_file": "new_file.txt",
            },
            redirect_url=reverse("committees:nextcloud:cloud_overview", kwargs={"group_id": self.association_group}),
        )


class CloudFileSyncInstructionsViewTestCase(TestFolderMixin, TestCase):
    url_name = "nextcloud:folder_sync_help"

    def test_fixed_values(self):
        self.assertTrue(issubclass(CloudFileSyncInstructionsView, AssociationGroupMixin))
        self.assertTrue(issubclass(CloudFileSyncInstructionsView, FolderMixin))
        self.assertTrue(issubclass(CloudFileSyncInstructionsView, TemplateView))
        self.assertEqual(
            CloudFileSyncInstructionsView.template_name,
            "nextcloud_integration/committees/committee_cloud_sync_instructions.html",
        )

    def test_successful_get(self):
        self.assertValidGetResponse()


@patch("nextcloud_integration.committee_pages.views.refresh_status")
class CloudFolderRefreshViewTestCase(TestFolderMixin, TestCase):
    url_name = "nextcloud:folder_refresh"

    def test_fixed_values(self, mock):
        self.assertTrue(issubclass(CloudFolderRefreshView, AssociationGroupMixin))
        self.assertTrue(issubclass(CloudFolderRefreshView, NextcloudConnectionViewMixin))
        self.assertTrue(issubclass(CloudFolderRefreshView, FolderMixin))
        self.assertTrue(issubclass(CloudFolderRefreshView, View))
        self.assertEqual(CloudFolderRefreshView.http_method_names, ["post"])

    def test_succesful_post(self, mock):
        self.assertValidPostResponse(
            data={},
            redirect_url=reverse("committees:nextcloud:cloud_overview", kwargs={"group_id": self.association_group}),
        )

    def test_succesful_post_message(self, mock):
        response = self.client.post(self.get_base_url(), data={}, follow=True)
        self.assertHasMessage(response, level=messages.SUCCESS)

    def test_succesful_post_missing_folder(self, mock):
        self.folder.is_missing = True
        self.folder.save()
        mock.return_value = False
        response = self.client.post(self.get_base_url(), data={}, follow=True)
        self.assertHasMessage(response, level=messages.WARNING, text="folder is missing")

    def test_succesful_post_missing_files(self, mock):
        self.folder.files.first().is_missing = True
        self.folder.files.first().save()
        mock.return_value = False
        response = self.client.post(self.get_base_url(), data={}, follow=True)
        self.assertHasMessage(response, level=messages.WARNING, text="folder has one or more missing files")
