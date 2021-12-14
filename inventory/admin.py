from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from core.admin import EmptyFieldListFilter
from inventory.models import *


class OwnershipInline(GenericTabularInline):
    model = Ownership
    extra = 0
    autocomplete_fields = ['member', 'group', 'added_by']


class OwnershipAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'content_object')
    list_display_links = ('id', 'owner')
    # Note search_fields does not work on GenericRelation fields
    search_fields = ['group__name', 'member__first_name', 'member__last_name']

    autocomplete_fields = ['member', 'group', 'added_by']
    list_filter = (
        'content_type',
        ('group', admin.RelatedOnlyFieldListFilter),
        ('member', EmptyFieldListFilter),
    )

admin.site.register(Ownership, OwnershipAdmin)

class OwnershipValueProxy(Ownership):
    class Meta:
        verbose_name = "Association inventory value"
        proxy = True

@admin.register(OwnershipValueProxy)
class OwnershipValues(admin.ModelAdmin):
    list_display = ('owner', 'content_object', 'value')
    list_display_links = ('owner',)
    list_filter = ('group',)
    fields = ('value',)

    def get_queryset(self, request):
        return super(OwnershipValues, self).get_queryset(request).filter(
            group__isnull=False
        )


class ItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'current_possession_count')
    list_display_links = ('id', 'name')
    search_fields = ['name']
    inlines = [OwnershipInline]
    list_filter = (
        ('ownerships__group', admin.RelatedOnlyFieldListFilter),
        ('ownerships__member', EmptyFieldListFilter),
    )

    @staticmethod
    def current_possession_count(obj):
        return obj.currently_in_possession().count()
    current_possession_count.short_description = 'Number of items at the association'

admin.site.register(MiscellaneousItem, ItemAdmin)
