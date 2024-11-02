from django.contrib import admin

from .forms import ActivityAdminForm, ActivityMomentAdminForm
from .models import (
    Activity,
    ActivitySlot,
    Participant,
    ActivityMoment,
    OrganiserLink,
    CoreActivityGrouping,
    Calendar,
    CalendarActivityLink,
)

from core.admin import DisableModificationsAdminMixin, MarkdownImageInline, URLLinkInlineAdminMixin
from utils.forms import RequestUserToFormModelAdminMixin


class MarkdownImageInlineAdmin(RequestUserToFormModelAdminMixin, admin.ModelAdmin):
    class Media:
        css = {"all": ("css/martor-admin.css",)}

    # Add MarkdownImages to the Admin's Inline models
    #   Note: Appending classes to get_inlines(..) makes them load additional times upon a page reload
    def get_inline_instances(self, request, obj=None):
        instances = super().get_inline_instances(request, obj=obj)
        instances.append(MarkdownImageInline(self.model, self.admin_site))
        return instances


########################################################
# INLINES WITH LINK
########################################################
class ActivityMomentInline(URLLinkInlineAdminMixin, DisableModificationsAdminMixin, admin.TabularInline):
    model = ActivityMoment
    extra = 0
    readonly_fields = ["last_updated", "get_url"]
    fields = ["recurrence_id", "status", "local_title", "get_url"]
    ordering = ("-recurrence_id",)


class ActivitySlotInline(URLLinkInlineAdminMixin, DisableModificationsAdminMixin, admin.TabularInline):
    model = ActivitySlot
    extra = 0
    readonly_fields = ["get_url"]
    fields = ["title", "location", "owner", "max_participants", "get_url"]
    ordering = ("title",)


########################################################
# OTHER
########################################################


class OrganiserInline(admin.TabularInline):
    model = OrganiserLink
    extra = 0


@admin.register(CoreActivityGrouping)
class CoreActivityGroupingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "identifier",
    )
    list_filter = ["identifier"]


@admin.register(Activity)
class ActivityAdmin(MarkdownImageInlineAdmin):
    form = ActivityAdminForm

    def is_recurring(self, obj):
        return obj.is_recurring

    is_recurring.boolean = True

    list_display = (
        "id",
        "title",
        "start_date",
        "is_recurring",
        "subscriptions_required",
    )
    list_filter = [
        "subscriptions_required",
        "start_date",
    ]
    list_display_links = ("id", "title")
    date_hierarchy = "start_date"
    search_fields = ["title"]
    search_help_text = "Search for title"
    autocomplete_fields = [
        "author",
    ]

    inlines = [OrganiserInline, ActivityMomentInline]

    def get_view_on_site_url(self, obj=None):
        if hasattr(obj, "get_absolute_url") and obj.get_absolute_url() is None:
            return None
        return super().get_view_on_site_url(obj=obj)


@admin.register(ActivityMoment)
class ActivityMomentAdmin(MarkdownImageInlineAdmin):
    form = ActivityMomentAdminForm

    list_filter = ["recurrence_id", "local_start_date", "parent_activity__type"]
    date_hierarchy = "recurrence_id"
    search_fields = ["local_title", "parent_activity__title"]
    search_help_text = "Search for title"
    autocomplete_fields = [
        "parent_activity",
    ]

    inlines = [ActivitySlotInline]

    def activity_moment_has_changes(obj):
        """Check if this ActivityModel has any data it overwrites"""
        for field in obj._meta.local_fields:
            # Check for all local_ fields if it is None, if not, it overwrites an attribute
            if field.name.startswith("local_"):
                local_value = getattr(obj, field.name)
                if local_value is not None and local_value != "":
                    return True
        return False

    activity_moment_has_changes.boolean = True
    activity_moment_has_changes.short_description = "Is tweaked"
    list_display = [
        "title",
        "recurrence_id",
        "local_start_date",
        "last_updated",
        "full_day",
        "is_part_of_recurrence",
        activity_moment_has_changes,
    ]


class CalendarActivityLinkInline(admin.TabularInline):
    model = CalendarActivityLink
    extra = 0


@admin.register(Calendar)
class CalendarAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "connected_activities")
    list_display_links = ("id", "name")

    inlines = [CalendarActivityLinkInline]

    def connected_activities(self, obj):
        return obj.activities.count()


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0
    autocomplete_fields = [
        "user",
    ]


class ActivitySlotAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "parent_activitymoment", "owner")
    list_filter = ["parent_activitymoment__recurrence_id"]
    list_display_links = ("id", "title")
    date_hierarchy = "parent_activitymoment__recurrence_id"
    search_fields = ["parent_activitymoment__parent_activity__title", "parent_activitymoment__local_title", "title"]
    search_help_text = "Search for slot name or activity title"
    autocomplete_fields = [
        "parent_activitymoment",
    ]

    # Not supported yet
    exclude = ("start_date", "end_date")

    inlines = [ParticipantInline]


admin.site.register(ActivitySlot, ActivitySlotAdmin)
admin.site.register(CalendarActivityLink)
