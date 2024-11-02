from django.contrib import admin
from achievements.admin import AchievementItemInline

from boardgames.models import BoardGame
from inventory.admin import ItemAdmin


class BoardgameAdmin(ItemAdmin):
    inlines = [*ItemAdmin.inlines, AchievementItemInline]


admin.site.register(BoardGame, BoardgameAdmin)
