from django.contrib import admin

from boardgames.models import BoardGame
from core.admin import EmptyFieldListFilter
from inventory.admin import OwnershipInline


class BoardGameAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'current_possession_count')
    list_display_links = ('id', 'name')
    search_fields = ['name']
    inlines = [OwnershipInline,]
    list_filter = (
        ('ownerships__group', admin.RelatedOnlyFieldListFilter),
        ('ownerships__member', EmptyFieldListFilter),
    )

    @staticmethod
    def current_possession_count(obj):
        return obj.currently_in_possession().count()
    current_possession_count.short_description = 'Number of items at the association'



admin.site.register(BoardGame, BoardGameAdmin)
