from django.contrib import admin
from django.utils.timezone import localtime

from .forms import ActivityAdminForm, ActivityMomentAdminForm
from .models import Activity, ActivitySlot, Participant, ActivityMoment, OrganiserLink, CoreActivityGrouping, \
    Calendar, CalendarActivityLink

from core.admin import MarkdownImageInline
from utils.forms import RequestUserToFormModelAdminMixin

class MarkdownImageInlineAdmin(RequestUserToFormModelAdminMixin, admin.ModelAdmin):
    class Media:
        css = {
             'all': ('css/martor-admin.css',)
        }

    # Add MarkdownImages to the Admin's Inline models
    # TODO: Remove in Django 3.0
    def get_inline_instances(self, request, obj=None):
        instances = super().get_inline_instances(request, obj=obj)
        instances.append(MarkdownImageInline(self.model, self.admin_site))
        return instances

    # Add MarkdownImages to the Admin's Inline models
    # TODO: Django 3.0
    # def get_inlines(self, request, obj):
    #     inlines = super().get_inlines(request, obj=obj)
    #     inlines.append(MarkdownImageInline)
    #     return inlines


class OrganiserInline(admin.TabularInline):
    model = OrganiserLink
    extra = 0

@admin.register(CoreActivityGrouping)
class CoreActivityGroupingAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier',)
    list_filter = ['identifier']

@admin.register(Activity)
class ActivityAdmin(MarkdownImageInlineAdmin):
    form = ActivityAdminForm

    def is_recurring(self, obj):
        return obj.is_recurring
    is_recurring.boolean = True

    list_display = ('id', 'title', 'start_date', 'is_recurring', 'subscriptions_required', )
    list_filter = ['subscriptions_required', 'start_date', 'is_public']
    list_display_links = ('id', 'title')
    date_hierarchy = 'start_date'
    search_fields = ['title']
    autocomplete_fields = ['author',]

    inlines = [OrganiserInline]

    def get_view_on_site_url(self, obj=None):
        if hasattr(obj, 'get_absolute_url') and obj.get_absolute_url() is None:
            return None
        return super().get_view_on_site_url(obj=obj)


@admin.register(ActivityMoment)
class ActivityMomentAdmin(MarkdownImageInlineAdmin):
    form = ActivityMomentAdminForm

    list_filter = ['recurrence_id', 'local_start_date']
    date_hierarchy = 'recurrence_id'
    search_fields = ['local_title', 'parent_activity__title']
    autocomplete_fields = ['parent_activity',]

    def activity_moment_has_changes(obj):
        """ Check if this ActivityModel has any data it overwrites """
        for field in obj._meta.local_fields:
            # Check for all local_ fields if it is None, if not, it overwrites an attribute
            if field.name.startswith("local_"):
                local_value = getattr(obj, field.name)
                if local_value is not None and local_value != "":
                    return True
        return False
    activity_moment_has_changes.boolean = True
    activity_moment_has_changes.short_description = 'Is tweaked'
    list_display = ["title", "recurrence_id", "local_start_date", "last_updated", "is_part_of_recurrence", activity_moment_has_changes]



class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0
    autocomplete_fields = ['user',]


class ActivitySlotAdmin(admin.ModelAdmin):
    def recurrence_id_with_day(self, obj):
        if obj.recurrence_id is not None:
            return localtime(obj.recurrence_id).strftime("%a, %d %b %Y, %H:%M")
        return None
    recurrence_id_with_day.admin_order_field = 'recurrence_id'
    recurrence_id_with_day.short_description = 'Activity Start Date'

    list_display = ('id', 'title', 'parent_activity', 'recurrence_id_with_day', 'owner')
    list_filter = ['recurrence_id']
    list_display_links = ('id', 'title')
    date_hierarchy = 'recurrence_id'
    search_fields = ['parent_activity__title', 'title']
    autocomplete_fields = ['parent_activity',]

    # Not supported yet
    exclude = ('start_date', 'end_date')

    inlines = [ParticipantInline]

admin.site.register(ActivitySlot, ActivitySlotAdmin)
admin.site.register(Calendar)
admin.site.register(CalendarActivityLink)
