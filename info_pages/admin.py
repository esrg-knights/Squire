from django.contrib import admin
from info_pages.models import InfoPage

@admin.register(InfoPage)
class InfoPageAdmin(admin.ModelAdmin):

    list_display = ('id', 'title')
    list_display_links = ('id', 'title')
    search_fields = ('title',)
