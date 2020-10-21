from django.contrib import admin
from django.contrib.auth.models import Group
from .models import PresetImage, ExtendedGroup

class PresetImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image', 'selectable')
    list_filter = ['selectable']
    list_display_links = ('id', 'name')

admin.site.register(PresetImage, PresetImageAdmin)

# Register our own group model instead
admin.site.unregister(Group)
admin.site.register(ExtendedGroup)
