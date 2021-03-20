from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from dynamic_preferences.admin import GlobalPreferenceAdmin
from dynamic_preferences.models import GlobalPreferenceModel

from .models import PresetImage


class PresetImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image', 'selectable')
    list_filter = ['selectable']
    list_display_links = ('id', 'name')

admin.site.register(PresetImage, PresetImageAdmin)


# We want to hide some global preference fields in the admin panel
class SquireGlobalPreferencesAdmin(GlobalPreferenceAdmin):
    list_display = ('id', 'verbose_name', 'section_name')
    list_display_links = ('id', 'verbose_name')

    fields = ('raw_value', 'default_value', 'section_name')
    readonly_fields = ('section_name', 'default_value')
    search_fields = ['name', 'section']

    # For "MtM" relations, we have a more user-friendly display method
    # that we want to show instead
    def default_value(self, obj):
        if hasattr(obj.preference, 'default_display'):
            return obj.preference.default_display
        if hasattr(obj.preference, 'get_default_display'):
            return obj.preference.get_default_display()
        return obj.preference.default
    default_value.short_description = _("Default Value")

admin.site.unregister(GlobalPreferenceModel)
admin.site.register(GlobalPreferenceModel, SquireGlobalPreferencesAdmin)
