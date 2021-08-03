from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from inventory.models import *


class OwnershipInline(GenericTabularInline):
    model = Ownership
    extra = 1


class BoardGameAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'current_possession_count')
    list_display_links = ('id', 'name')
    search_fields = ['name']
    inlines = (OwnershipInline,)

    def current_possession_count(self, obj):
        return obj.currently_in_possession().count()
    current_possession_count.short_description = 'Number of items at the association'


class OwnershipAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'content_object')
    list_display_links = ('id', 'owner')
    # Note search_fields does not work on GenericRelation fields
    search_fields = ['group__name', 'member__first_name', 'member__last_name']

    autocomplete_fields = ['member', 'group']


admin.site.register(Ownership, OwnershipAdmin)
admin.site.register(BoardGame, BoardGameAdmin)
