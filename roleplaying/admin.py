from django.contrib import admin

from core.admin import EmptyFieldListFilter
from inventory.admin import OwnershipInline
from roleplaying.models import *


class RoleplaySystemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'more_info_url', 'is_public', 'get_num_items')
    list_display_links = ('id', 'name')
    search_fields = ['name']
    list_filter = (
        'is_public',
    )

    @staticmethod
    def get_num_items(obj):
        return obj.items.count()
    get_num_items.short_description  = 'Number of items for system'

admin.site.register(RoleplayingSystem, RoleplaySystemAdmin)


class RoleplayItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'system', 'current_possession_count')
    list_display_links = ('id', 'name')
    search_fields = ['name']
    inlines = [OwnershipInline,]
    autocomplete_fields = ['system']
    list_filter = (
        'system',
        ('ownerships__group', admin.RelatedOnlyFieldListFilter),
        ('ownerships__member', EmptyFieldListFilter),
    )

    @staticmethod
    def current_possession_count(obj):
        return obj.currently_in_possession().count()
    current_possession_count.short_description = 'Number of items at the association'

admin.site.register(RoleplayingItem, RoleplayItemAdmin)
