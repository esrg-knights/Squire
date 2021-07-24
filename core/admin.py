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

# Global preferences admin panel.
#   We want to change the way some preference fields are rendered
class SquireGlobalPreferencesAdmin(GlobalPreferenceAdmin):
    list_display = ('id', 'verbose_name', 'description', 'section_name')
    list_display_links = ('id', 'verbose_name')

    fields = ('verbose_name', 'description', 'raw_value', 'default_value', 'section_name')
    readonly_fields = ('verbose_name', 'description', 'section_name', 'default_value')
    search_fields = ['name', 'verbose_name', 'description', 'section']

    # Description of the permission
    def description(self, obj):
        return obj.preference.description or '-'

    # For MtM-relations, display text instead of primary keys
    def default_value(self, obj):
        if hasattr(obj.preference, 'default_display'):
            return obj.preference.default_display
        if hasattr(obj.preference, 'get_default_display'):
            return obj.preference.get_default_display()
        return obj.preference.default
    default_value.short_description = _("Default Value")

# Use our custom admin panel instead
admin.site.unregister(GlobalPreferenceModel)
admin.site.register(GlobalPreferenceModel, SquireGlobalPreferencesAdmin)
