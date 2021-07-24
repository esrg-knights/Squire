from django.contrib import admin

from inventory.models import *


class BoardGameAdmin(admin.ModelAdmin):
    list_display = ('id', '__str__', 'currently_in_possession')



admin.site.register(Ownership)
admin.site.register(BoardGame, BoardGameAdmin)
