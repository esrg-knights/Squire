from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from .models import PresetImage, ExtendedGroup

class PresetImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image', 'selectable')
    list_filter = ['selectable']
    list_display_links = ('id', 'name')

admin.site.register(PresetImage, PresetImageAdmin)


class ExtendedGroupAdmin(DjangoGroupAdmin):
    list_display = ('id', 'name', 'description', 'is_public')
    list_filter = ['is_public']
    list_display_links = ('id', 'name')

    readonly_fields = ['is_core_group']

    fieldsets = [
        (None,  {'fields': ['name', 'description', 'is_core_group', 'is_public', 'permissions']}),
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj is None or not obj.is_core_group:
            return self.readonly_fields
        return self.readonly_fields + ['name']
        
    
    def has_delete_permission(self, request, obj=None):
        return obj is None or not obj.is_core_group

# Register our own group model instead
admin.site.unregister(Group)
admin.site.register(ExtendedGroup, ExtendedGroupAdmin)
