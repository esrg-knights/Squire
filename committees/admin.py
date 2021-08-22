from django.contrib import admin

from committees.models import AssociationGroup, GroupExternalUrls


admin.site.register(AssociationGroup)
admin.site.register(GroupExternalUrls)
