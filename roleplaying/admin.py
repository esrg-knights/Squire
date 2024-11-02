from django.contrib import admin
from achievements.admin import AchievementItemInline

from activity_calendar.admin import MarkdownImageInlineAdmin
from inventory.admin import ItemAdmin
from roleplaying.forms import RoleplayingSystemAdminForm
from roleplaying.models import *


class RoleplaySystemAdmin(MarkdownImageInlineAdmin):
    form = RoleplayingSystemAdminForm
    list_display = ("id", "name", "more_info_url", "is_public", "get_num_items")
    list_display_links = ("id", "name")
    search_fields = ["name"]
    search_help_text = "Search for name"
    list_filter = ("is_public",)
    inlines = [AchievementItemInline]

    @staticmethod
    def get_num_items(obj):
        return obj.items.count()

    get_num_items.short_description = "Number of items for system"


admin.site.register(RoleplayingSystem, RoleplaySystemAdmin)


class RoleplayItemAdmin(ItemAdmin):
    list_display = ("id", "name", "system", "current_possession_count")
    autocomplete_fields = ["system"]
    list_filter = (
        "system",
        *ItemAdmin.list_filter,
    )


admin.site.register(RoleplayingItem, RoleplayItemAdmin)
