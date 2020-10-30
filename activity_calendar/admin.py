from django.contrib import admin
from .models import Activity, ActivitySlot, Participant, ActivityMoment
from django.utils.timezone import localtime



class ActivityAdmin(admin.ModelAdmin):
    def is_recurring(self, obj):
        return obj.is_recurring
    is_recurring.boolean = True

    list_display = ('id', 'title', 'start_date', 'is_recurring', 'subscriptions_required', )
    list_filter = ['subscriptions_required']
    list_display_links = ('id', 'title')

admin.site.register(Activity, ActivityAdmin)


@admin.register(ActivityMoment)
class ActivityMomentAdmin(admin.ModelAdmin):
    fields = ['parent_activity', 'recurrence_id', 'local_description', 'local_location', 'local_max_participants']


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
