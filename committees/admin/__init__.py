from django.contrib import admin

from committees.models import AssociationGroup, GroupExternalUrl
from .options import GroupExternalURLAdmin, AssociationGroupAdmin, GroupPanelAccessAdmin
from .models import AssociationGroupPanelControl

admin.site.register(AssociationGroup, AssociationGroupAdmin)
admin.site.register(GroupExternalUrl, GroupExternalURLAdmin)
admin.site.register(AssociationGroupPanelControl, GroupPanelAccessAdmin)
