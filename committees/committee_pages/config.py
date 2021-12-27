from django.urls import path, include, reverse

from committees.committeecollective import CommitteeBaseConfig

from committees.committee_pages.views import *


class AssociationGroupHomeConfig(CommitteeBaseConfig):
    url_keyword = 'main'
    name = 'Overview'
    icon_class = 'fas fa-users'
    url_name = 'group_general'
    order_value = 10

    def get_urls(self):
        """ Builds a list of urls """
        return [
            path('', AssociationGroupDetailView.as_view(config=self), name='group_general'),
            path('update/', AssociationGroupUpdateView.as_view(config=self), name='group_update'),
            path('members/', AssociationGroupMembersView.as_view(config=self), name='group_members'),
            path('members/edit/', AssociationGroupMemberUpdateView.as_view(config=self), name='group_members_edit'),
            path('quicklinks/', include([
                path('', AssociationGroupQuickLinksView.as_view(config=self), name='group_quicklinks'),
                path('edit/', AssociationGroupQuickLinksAddOrUpdateView.as_view(config=self), name='group_quicklinks_edit'),
                path('<int:quicklink_id>/delete/', AssociationGroupQuickLinksDeleteView.as_view(config=self), name='group_quicklink_delete'),
            ])),
        ]
