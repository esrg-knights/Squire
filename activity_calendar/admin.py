from django.contrib import admin
from django.utils.timezone import localtime

from .forms import ActivityAdminForm, ActivityMomentAdminForm
from .models import Activity, ActivitySlot, Participant, ActivityMoment

from core.admin import MarkdownImageInline


class MarkdownImageInlineAdmin(admin.ModelAdmin):
    class Media:
        css = {
             'all': ('css/martor.css',)
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

    # Pass the requesting user to the form
    #   NB: This method should return a _class_
    #   Ideally, we'd only need to provide form kwargs somewhere instead of
    #       using this hacky structure. However, for some reason, Django
    #       does not seem to provide any way to do so within the admin panel:
    #       - For normal view-based classes, there's get_form_kwargs(..)
    #       - For Inlines (in a future version of Django 3.x), there's get_formset_kwargs(..)
    #       Neither of these work for the standard admin views
    # Related links:
    # - https://stackoverflow.com/questions/2864955/django-how-to-get-current-user-in-admin-forms
    # - https://code.djangoproject.com/ticket/26607
    def get_form(self, request, obj=None, **kwargs):
        MDForm = super().get_form(request, obj, **kwargs)

        class MarkdownFormWithKwargs(MDForm):
            def __new__(cls, *args, **kwargs):
                return MDForm(*args, user=request.user, **kwargs)
        return MarkdownFormWithKwargs


class ActivityAdmin(MarkdownImageInlineAdmin):
    form = ActivityAdminForm

    def is_recurring(self, obj):
        return obj.is_recurring
    is_recurring.boolean = True

    list_display = ('id', 'title', 'start_date', 'is_recurring', 'subscriptions_required', )
    list_filter = ['subscriptions_required']
    list_display_links = ('id', 'title')

    def get_view_on_site_url(self, obj=None):
        if hasattr(obj, 'get_absolute_url') and obj.get_absolute_url() is None:
            return None
        return super().get_view_on_site_url(obj=obj)

admin.site.register(Activity, ActivityAdmin)


@admin.register(ActivityMoment)
class ActivityMomentAdmin(MarkdownImageInlineAdmin):
    form = ActivityMomentAdminForm

    list_filter = ['parent_activity']

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
