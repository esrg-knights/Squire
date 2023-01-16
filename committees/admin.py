from django.contrib import admin
from django.contrib.admin.filters import RelatedOnlyFieldListFilter

from activity_calendar.admin import MarkdownImageInlineAdmin
from committees.forms import AssociationGroupAdminForm
from committees.models import *


class MembershipInline(admin.TabularInline):
    model = AssociationGroupMembership
    extra = 0
    autocomplete_fields = ['member',]

@admin.register(AssociationGroup)
class AssociationGroupAdmin(MarkdownImageInlineAdmin):
    form = AssociationGroupAdminForm

    list_display = ('id', 'name', 'shorthand',)
    list_filter = ['type', 'is_public']
    list_display_links = ('id', 'name')
    search_fields = ('site_group__name', 'shorthand', 'contact_email')
    fields = [('name', 'shorthand', 'site_group',), ('type', 'is_public'), 'icon', 'short_description',
              'permissions',
              'long_description',
              'contact_email', 'instructions']

    inlines = [MembershipInline]
    autocomplete_fields = ['site_group',]
    filter_horizontal = ("permissions",)


@admin.register(GroupExternalUrl)
class GroupExternalURLAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'association_group')
    list_filter = [
        ('association_group', RelatedOnlyFieldListFilter)
    ]
    list_display_links = ('id', 'name')
    search_fields = ('asssociation_group__site_group__name', 'name')

    autocomplete_fields = ['association_group',]
