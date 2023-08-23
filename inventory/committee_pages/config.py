from django.urls import path, reverse

from committees.committeecollective import CommitteeBaseConfig

from .views import AssociationGroupInventoryView, AssociationGroupItemLinkUpdateView


class InventoryConfig(CommitteeBaseConfig):
    url_keyword = "inventory"
    name = "Inventory"
    icon_class = "fas fa-archive"
    url_name = "group_inventory"
    order_value = 50
    group_requires_permission = "inventory.view_ownership"

    def get_urls(self):
        """Builds a list of urls"""
        return [
            path("", AssociationGroupInventoryView.as_view(config=self), name="group_inventory"),
            path(
                "<int:ownership_id>/", AssociationGroupItemLinkUpdateView.as_view(config=self), name="group_inventory"
            ),
        ]

    def get_local_quicklinks(self, association_group):
        quicklinks = super(InventoryConfig, self).get_local_quicklinks(association_group)
        for permission in association_group.site_group.permissions.all():
            if permission.codename.startswith("maintain_ownerships_for"):
                quicklinks.append(
                    {
                        "name": f"{permission.content_type.name} catalogue",
                        "url": reverse("inventory:catalogue", kwargs={"type_id": permission.content_type}),
                    }
                )
        return quicklinks
