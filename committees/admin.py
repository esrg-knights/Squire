from django.contrib import admin

from committees.models import *


class MembershipInline(admin.TabularInline):
    model = AssociationGroupMembership
    extra = 1
    min_num = 0

@admin.register(AssociationGroup)
class AssociationGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'shorthand',)
    list_filter = ['type', 'is_public']
    list_display_links = ('id', 'name')
    search_fields = ('site_group__name', 'shorthand', 'contact_email')
    fields = [('site_group', 'shorthand'), ('type', 'is_public'), 'icon', 'short_description', 'long_description',
              'contact_email', 'instructions']

    inlines = [MembershipInline]

admin.site.register(GroupExternalUrl)
