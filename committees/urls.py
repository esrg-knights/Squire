from django.urls import path, include
from django.views.generic.base import RedirectView

from committees.views import *
from committees.config import get_all_configs


def get_urls():
    """
    Go over all installed apps and look for the urls file in the setup folder.
    This way we can assign the relevant setup views and the like to the modules instead of dumping it through
    a chain of apps.

    :return:
    """

    extra_urls = []
    # Try to load the setup config files
    for setup_config in get_all_configs():
        extra_urls.append(path(f'{setup_config.url_keyword}/', setup_config.urls))

    urls = [
        # Change Language helper view
        path('', RedirectView.as_view(url=reverse_lazy("committees:committees")), name='home'),
        path('committees/', CommitteeOverview.as_view(), name='committees'),
        path('guilds/', GuildOverview.as_view(), name='guilds'),
        path('boards/', BoardOverview.as_view(), name='boards'),
        path('<int:group_id>/', include([
            path('main/', include([
                path('', AssociationGroupDetailView.as_view(), name='group_general'),
                path('update/', AssociationGroupUpdateView.as_view(), name='group_update'),
                path('members/', AssociationGroupMembersView.as_view(), name='group_members'),
                path('members/edit/', AssociationGroupMemberUpdateView.as_view(), name='group_members_edit'),
                path('quicklinks/', include([
                    path('', AssociationGroupQuickLinksView.as_view(), name='group_quicklinks'),
                    path('edit/', AssociationGroupQuickLinksAddOrUpdateView.as_view(), name='group_quicklinks_edit'),
                    path('<int:quicklink_id>/delete/', AssociationGroupQuickLinksDeleteView.as_view(), name='group_quicklink_delete'),
                ])),
            ])),
            *extra_urls,
        ]))
    ]


    return urls, 'committees', 'committees'
