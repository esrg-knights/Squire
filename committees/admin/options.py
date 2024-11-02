from django.contrib import admin
from django.contrib.admin.filters import RelatedOnlyFieldListFilter

from activity_calendar.admin import MarkdownImageInlineAdmin
from committees.forms import AssociationGroupAdminForm
from committees.models import *
from .forms import AssociationGroupsTabAccessForm


class MembershipInline(admin.TabularInline):
    model = AssociationGroupMembership
    extra = 0
    autocomplete_fields = [
        "member",
    ]


class AssociationGroupAdmin(MarkdownImageInlineAdmin):
    form = AssociationGroupAdminForm

    list_display = (
        "id",
        "name",
        "shorthand",
    )
    list_filter = ["type", "is_public"]
    list_display_links = ("id", "name")
    search_fields = ("site_group__name", "shorthand", "contact_email")
    search_help_text = "Search for name, shorthand, or email"
    fields = [
        (
            "name",
            "shorthand",
            "site_group",
        ),
        ("type", "is_public"),
        "icon",
        "short_description",
        "permissions",
        "long_description",
        "contact_email",
        "instructions",
    ]

    inlines = [MembershipInline]
    autocomplete_fields = [
        "site_group",
    ]
    filter_horizontal = ("permissions",)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super(AssociationGroupAdmin, self).get_readonly_fields(request, obj))
        if not request.user.has_perm("auth.change_permission"):
            # In theory this should set the field to disabled, in reality the widget does not have a disabled state
            # So it removes the widget entirely. Not the cleanest solution in terms of UX, but it does its job
            readonly_fields.append("permissions")
        return readonly_fields


class GroupExternalURLAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "association_group")
    list_filter = [("association_group", RelatedOnlyFieldListFilter)]
    list_display_links = ("id", "name")
    search_fields = ("asssociation_group__site_group__name", "name")
    search_help_text = "Search for name"

    autocomplete_fields = [
        "association_group",
    ]


class GroupPanelAccessAdmin(admin.ModelAdmin):
    change_form_template = "committees/admin/change_group_tab_access.html"
    list_display = ("id", "name")
    list_display_links = ("id", "name")
    list_filter = ("type",)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def get_form(self, request, obj=None, change=False, **kwargs):
        return AssociationGroupsTabAccessForm
