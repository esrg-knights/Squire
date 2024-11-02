from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from .models import *


class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "priority")
    list_display_links = ("id", "name")
    search_fields = ("name",)
    search_help_text = "Search for name"


admin.site.register(Category, CategoryAdmin)


class ClaimantInline(admin.TabularInline):
    model = Claimant
    extra = 0
    autocomplete_fields = ["user"]


class AchievementAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "is_public")
    list_filter = ["category", "is_public"]
    list_display_links = ("id", "name")
    search_fields = ("name",)
    search_help_text = "Search for name"
    autocomplete_fields = ["category"]

    inlines = [ClaimantInline]


admin.site.register(Achievement, AchievementAdmin)


class AchievementItemInline(GenericTabularInline):
    model = AchievementItemLink
    extra = 0
    ordering = ("achievement__name",)
    autocomplete_fields = ["achievement"]


class AchievementItemLinkAdmin(admin.ModelAdmin):
    search_fields = ("achievement__name",)
    search_help_text = "Search for achievement name"
    list_display = ("id", "achievement", "content_object")
    list_display_links = ("id", "achievement")
    autocomplete_fields = ["achievement"]


admin.site.register(AchievementItemLink, AchievementItemLinkAdmin)
