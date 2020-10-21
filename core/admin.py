from django.contrib import admin
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
# Register our own group model instead
admin.site.unregister(Group)
admin.site.register(ExtendedGroup, ExtendedGroupAdmin)
