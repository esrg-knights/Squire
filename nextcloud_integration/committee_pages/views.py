from django.contrib import messages
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView, ListView, View
from django.urls import reverse

from committees.mixins import AssociationGroupMixin

from nextcloud_integration.models import SquireNextCloudFolder
from nextcloud_integration.utils import refresh_status
from nextcloud_integration.views import (
    FolderEditView,
    FolderCreateView,
    SyncFileToFolderView,
    FolderMixin,
    NextcloudConnectionViewMixin,
)


__all__ = [
    "CloudFoldersOverview",
    "CloudFolderEditView",
    "CloudFolderCreateView",
    "CloudFileSyncView",
    "CloudFileSyncInstructionsView",
    "CloudFolderRefreshView",
]


class CloudFoldersOverview(AssociationGroupMixin, ListView):
    template_name = "nextcloud_integration/committees/committee_cloud_folders_overview.html"
    model = SquireNextCloudFolder
    context_object_name = "folders"


class CloudFolderCreateView(AssociationGroupMixin, FolderCreateView):
    template_name = "nextcloud_integration/committees/committee_cloud_folder_add.html"
    permission_required = []

    def get_success_url(self):
        return reverse(
            "committees:nextcloud:cloud_overview",
            kwargs={
                "group_id": self.association_group.id,
            },
        )


class CloudFolderEditView(AssociationGroupMixin, FolderEditView):
    template_name = "nextcloud_integration/committees/committee_cloud_folder_edit.html"
    permission_required = []

    def get_success_url(self):
        return reverse(
            "committees:nextcloud:cloud_overview",
            kwargs={
                "group_id": self.association_group.id,
            },
        )


class CloudFileSyncView(AssociationGroupMixin, SyncFileToFolderView):
    template_name = "nextcloud_integration/committees/committee_cloud_folder_sync.html"

    def get_success_url(self):
        return reverse(
            "committees:nextcloud:cloud_overview",
            kwargs={
                "group_id": self.association_group.id,
            },
        )


class CloudFileSyncInstructionsView(AssociationGroupMixin, FolderMixin, TemplateView):
    template_name = "nextcloud_integration/committees/committee_cloud_sync_instructions.html"


class CloudFolderRefreshView(AssociationGroupMixin, NextcloudConnectionViewMixin, FolderMixin, View):
    http_method_names = ["post"]

    def post(self, *args, **kwargs):
        if refresh_status(self.folder):
            msg = f"All files for {self.folder.display_name} were present on the cloud"
            messages.success(request=self.request, message=msg)
        else:
            self.folder.refresh_from_db()
            if self.folder.is_missing:
                msg = f"The {self.folder.display_name} folder is missing. Contact the UUPS to fix this issue"
            else:
                msg = f"The {self.folder.display_name} folder has one or more missing files, their status have been changed"
            messages.warning(request=self.request, message=msg)
        return HttpResponseRedirect(self.get_redirect_url())

    def get_redirect_url(self):
        return reverse(
            "committees:nextcloud:cloud_overview",
            kwargs={
                "group_id": self.association_group.id,
            },
        )
