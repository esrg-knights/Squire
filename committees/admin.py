from django.contrib import admin

from committees.models import *


class MembershipInline(admin.TabularInline):
    model = AssociationGroupMembership
    extra = 0

@admin.register(AssociationGroup)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'shorthand',)
    list_filter = ['type', 'is_public']
    list_display_links = ('id', 'name')

    inlines = [MembershipInline]

admin.site.register(GroupExternalUrl)
