from django.contrib.contenttypes.models import ContentType
from django.urls import path, include, reverse

from committees.config import CommitteeConfig

from .views import AssociationGroupInventoryView, AssociationGroupItemLinkUpdateView


class InventoryConfig(CommitteeConfig):
    url_keyword = 'inventory'
    tab_select_keyword = 'tab_inventory'
    name = 'Inventory'
    url_name = 'committees:group_inventory'

    def get_urls(self):
        """ Builds a list of urls """
        return [
            path('', AssociationGroupInventoryView.as_view(config_class=InventoryConfig), name='group_inventory'),
            path('<int:ownership_id>/', AssociationGroupItemLinkUpdateView.as_view(config_class=InventoryConfig), name='group_inventory'),
        ]

    def get_local_quicklinks(self, association_group):
        quicklinks = super(InventoryConfig, self).get_local_quicklinks(association_group)
        for permission in association_group.site_group.permissions.all():
            if permission.codename.startswith('maintain_ownerships_for'):
                quicklinks.append({
                    'name': f'{permission.content_type} catalogue',
                    'url': reverse('inventory:catalogue', kwargs={'type_id': permission.content_type})
                })
        return quicklinks
