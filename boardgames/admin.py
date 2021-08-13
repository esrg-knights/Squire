from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from boardgames.models import BoardGame
from inventory.models import Ownership


class OwnershipInline(GenericTabularInline):
    model = Ownership
    extra = 0


class BoardGameAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'current_possession_count')
    list_display_links = ('id', 'name')
    search_fields = ['name']
    inlines = [OwnershipInline,]

    @staticmethod
    def current_possession_count(obj):
        return obj.currently_in_possession().count()
    current_possession_count.short_description = 'Number of items at the association'



admin.site.register(BoardGame, BoardGameAdmin)
