from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from import_export.admin import ExportActionMixin
from import_export.fields import Field
from import_export.forms import ExportForm
from import_export.formats.base_formats import CSV, ODS, TSV, XLSX
from import_export.resources import ModelResource

from inventory.models import *


class OwnershipInline(GenericTabularInline):
    model = Ownership
    extra = 0
    autocomplete_fields = ["member", "group", "added_by"]


class OwnershipAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "content_object")
    list_display_links = ("id", "owner")
    # Note search_fields does not work on GenericRelation fields
    search_fields = ["group__name", "member__first_name", "member__last_name"]
    search_help_text = "Search for group name, member name"

    autocomplete_fields = ["member", "group", "added_by"]
    list_filter = (
        "content_type",
        ("group", admin.RelatedOnlyFieldListFilter),
        ("member", admin.EmptyFieldListFilter),
    )


admin.site.register(Ownership, OwnershipAdmin)


class OwnershipValueProxy(Ownership):
    class Meta:
        verbose_name = "Association inventory value"
        proxy = True


class OwnershipValueResource(ModelResource):
    item_type = Field()
    item_name = Field()

    class Meta:
        model = OwnershipValueProxy
        fields = ("id", "group__name", "value", "item_type", "item_name")
        export_order = ("id", "group__name", "item_type", "item_name", "value")

    def dehydrate_item_type(self, ownership):
        return str(ownership.content_object.__class__.__name__)

    def dehydrate_item_name(self, ownership):
        return str(ownership.content_object.name)


@admin.register(OwnershipValueProxy)
class OwnershipValues(ExportActionMixin, admin.ModelAdmin):
    list_display = ("owner", "content_object", "value")
    list_display_links = ("owner",)
    list_filter = ("group",)
    fields = ("value",)

    export_form_class = ExportForm
    formats = (CSV, XLSX, TSV, ODS)
    resource_classes = [OwnershipValueResource]

    def get_queryset(self, request):
        return super(OwnershipValues, self).get_queryset(request).filter(group__isnull=False)


class ItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "current_possession_count")
    list_display_links = ("id", "name")
    search_fields = ["name"]
    search_help_text = "Search for name"
    inlines = [OwnershipInline]
    list_filter = (
        ("ownerships__group", admin.RelatedOnlyFieldListFilter),
        ("ownerships__member", admin.EmptyFieldListFilter),
    )

    @staticmethod
    def current_possession_count(obj):
        return obj.currently_in_possession().count()

    current_possession_count.short_description = "Number of items at the association"


admin.site.register(MiscellaneousItem, ItemAdmin)
