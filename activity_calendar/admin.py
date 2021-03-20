from django.contrib import admin
from django.utils.timezone import localtime

from .forms import ActivityAdminForm
from .models import Activity, ActivitySlot, Participant, ActivityMoment

class ActivityAdmin(admin.ModelAdmin):
    form = ActivityAdminForm

    class Media:
        css = {
             'all': ('css/martor.css',)
        }

    def is_recurring(self, obj):
        return obj.is_recurring
    is_recurring.boolean = True

    list_display = ('id', 'title', 'start_date', 'is_recurring', 'subscriptions_required', )
    list_filter = ['subscriptions_required']
    list_display_links = ('id', 'title')

admin.site.register(Activity, ActivityAdmin)




@admin.register(ActivityMoment)
class ActivityMomentAdmin(admin.ModelAdmin):
    list_filter = ['parent_activity']
    fields = ['parent_activity', 'recurrence_id', 'local_description', 'local_location', 'local_max_participants']

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
    list_display = ["title", "recurrence_id", "last_updated", activity_moment_has_changes]





class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0


class ActivitySlotAdmin(admin.ModelAdmin):
    def recurrence_id_with_day(self, obj):
        if obj.recurrence_id is not None:
            return localtime(obj.recurrence_id).strftime("%a, %d %b %Y, %H:%M")
        return None
    recurrence_id_with_day.admin_order_field = 'recurrence_id'
    recurrence_id_with_day.short_description = 'Activity Start Date'

    list_display = ('id', 'title', 'parent_activity', 'recurrence_id_with_day', 'owner')
    list_filter = ['parent_activity', 'recurrence_id']
    list_display_links = ('id', 'title')

    # Not supported yet
    exclude = ('start_date', 'end_date')

    inlines = [ParticipantInline]

admin.site.register(ActivitySlot, ActivitySlotAdmin)
