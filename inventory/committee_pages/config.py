from django.urls import path, include

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
