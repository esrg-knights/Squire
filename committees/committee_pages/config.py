from django.urls import path, include, reverse

from committees.committeecollective import CommitteeBaseConfig
from committees.committee_pages.views import *

from committees.committee_pages.options import settings


class AssociationGroupHomeConfig(CommitteeBaseConfig):
    name = 'Overview'
    icon_class = 'fas fa-users'
    url_name = 'group_general'
    order_value = 1

    _home_page_filters = {}

    def get_home_view(self, request, *args, group_id=None, **kwargs):
        """ Select which view class needs to be used. Defaults to AssociationGroupDetailView """
        display_view_class = None
        for filter, view_class in self._home_page_filters.values():
            if filter(group_id):
                display_view_class = view_class
                break
        display_view_class = display_view_class or AssociationGroupDetailView

        return display_view_class.as_view(config=self)(request, *args, group_id=group_id, **kwargs)

    def get_urls(self):
        """ Builds a list of urls """
        return [
            path('', self.get_home_view, name='group_general'),
        ]

    @classmethod
    def add_filter(cls, filter, view_class):
        """
        Adds a check for a custom home view
        :param filter: A method or callable that takes 'association_group' as an input argument and returns a boolean
        :param view_class: the view class (uninitialised)
        """
        cls._home_page_filters[filter.__name__] = (filter, view_class)


class AssociationGroupSettingsConfig(CommitteeBaseConfig):
    url_keyword = 'settings'
    name = 'Settings'
    icon_class = 'fas fa-cog'
    url_name = 'settings_home'
    order_value = 10

    def get_urls(self):
        """ Builds a list of urls """
        urls = [
            path('', AssociationGroupSettingsView.as_view(config=self), name='settings_home'),
            *settings.urls(self)
        ]
        return urls

    @property
    def settings(self):
        return settings

