from django.contrib import admin

from inventory.models import *


class BoardGameAdmin(admin.ModelAdmin):
    list_display = ('id', '__str__', 'current_possession_count')

    def current_possession_count(self, obj):
        return obj.currently_in_possession().count()
    current_possession_count.short_description = 'Number of items at the association'



admin.site.register(Ownership)
admin.site.register(BoardGame, BoardGameAdmin)
