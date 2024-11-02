from django.contrib import admin

from nextcloud_integration.models import SquireNextCloudFolder, SquireNextCloudFile


@admin.register(SquireNextCloudFolder)
class NCFolderAdmin(admin.ModelAdmin):
    list_display = ("id", "display_name", "description", "is_missing")
    list_display_links = ("id", "display_name")
    search_fields = ["display_name", "description"]
    search_help_text = "Search for name, description"

    list_filter = ("is_missing", "requires_membership", "on_overview_page")


@admin.register(SquireNextCloudFile)
class NCFileAdmin(admin.ModelAdmin):
    list_display = ("id", "display_name", "description", "folder_name")
    list_display_links = ("id", "display_name")
    list_filter = (
        "folder__display_name",
        "is_missing",
        "connection",
    )
    search_fields = ["display_name", "description", "folder__display_name"]
    search_help_text = "Search for name, description, folder name"
    readonly_fields = ["connection"]

    def folder_name(self, file):
        return file.folder.display_name
