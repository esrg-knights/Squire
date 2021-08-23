from django.urls import path, include, reverse_lazy
from django.views.generic.base import RedirectView

from committees.views import *
from committees.models import AssociationGroup


app_name = 'committees'

urlpatterns = [
    # Change Language helper view
    path('', RedirectView.as_view(url=reverse_lazy("committees:committees")), name='home'),
    path('committees/', CommitteeOverview.as_view(), name='committees'),
    path('guilds/', GuildOverview.as_view(), name='guilds'),
    path('boards/', BoardOverview.as_view(), name='boards'),
    path('<int:group_id>/', include([
        path('', AssociationGroupDetailView.as_view(), name='group_general'),
        path('update/', AssociationGroupUpdateView.as_view(), name='group_update'),
        path('quicklinks/', include([
            path('', AssociationGroupQuickLinksView.as_view(), name='group_quicklinks'),
            path('<int:quicklink_id>/', AssociationGroupQuickLinksView.as_view(), name='group_quicklinks'),
            path('<int:quicklink_id>/delete/', AssociationGroupQuickLinksDeleteView.as_view(), name='group_quicklink_delete'),
        ])),
        path('inventory/', AssociationGroupInventoryView.as_view(), name='group_inventory'),
        path('inventory/<int:ownership_id>', GroupItemLinkUpdateView.as_view(), name='group_inventory'),
    ]))
]
