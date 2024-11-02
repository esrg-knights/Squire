from django.urls import path, include, reverse

from committees.committeecollective import CommitteeBaseConfig

from nextcloud_integration.committee_pages.views import *


class NextcloudGroupConfig(CommitteeBaseConfig):
    url_keyword = "cloud"
    name = "Cloud storage"
    icon_class = "fas fa-cloud  "
    url_name = "nextcloud:cloud_overview"
    order_value = 12
    namespace = "nextcloud"
    group_requires_permission = "nextcloud_integration.change_squirenextcloudfolder"

    def get_urls(self):
        """Builds a list of urls"""
        return [
            path("", CloudFoldersOverview.as_view(config=self), name="cloud_overview"),
            path("add/", CloudFolderCreateView.as_view(config=self), name="cloud_add_folder"),
            path(
                "<slug:folder_slug>/",
                include(
                    [
                        path("edit/", CloudFolderEditView.as_view(config=self), name="folder_edit"),
                        path("sync/", CloudFileSyncView.as_view(config=self), name="folder_sync_file"),
                        path(
                            "sync/help/", CloudFileSyncInstructionsView.as_view(config=self), name="folder_sync_help"
                        ),
                        path("refresh/", CloudFolderRefreshView.as_view(config=self), name="folder_refresh"),
                    ]
                ),
            ),
        ]
