from django.contrib import admin

from committees.models import AssociationGroup, GroupExternalUrl


admin.site.register(AssociationGroup)
admin.site.register(GroupExternalUrl)
