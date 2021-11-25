from django.contrib import admin

from user_interaction.models import Pin

class PinAdmin(admin.ModelAdmin):
    date_hierarchy = 'publish_date'

    list_display = ('id', 'pintype', 'title', 'content_object', 'local_visibility', 'publish_date')
    list_display_links = ('id', 'pintype')
    list_filter = ('pintype',)
    search_fields = ('title', 'uploader__username',)
    readonly_fields = ('creation_date', 'id', 'author')

# admin.site.register(Pin, PinAdmin)
admin.site.register(Pin)
