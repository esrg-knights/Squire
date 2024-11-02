from django.urls import path

from committees.committeecollective import CommitteeBaseConfig
from committees.committee_pages.views import *

from committees.committee_pages.options import settings_options_registry


class AssociationGroupHomeConfig(CommitteeBaseConfig):
    name = "Home"
    icon_class = "fas fa-home"
    url_name = "group_general"
    order_value = 1

    _home_page_filters = {}

    def _get_filters(self):
        """Returns an iterable of tuples (filter, view_class) for the various possible views"""
        return self._home_page_filters.values()

    def get_home_view(self, request, *args, group_id=None, **kwargs):
        """Select which view class needs to be used. Defaults to AssociationGroupDetailView"""
        # Note: group_id is an association_group instance, the id in the name is due to a previous code state
        display_view_class = None
        for filter, view_class in self._get_filters():
            if filter(group_id):
                display_view_class = view_class
                break
        display_view_class = display_view_class or AssociationGroupDetailView

        return display_view_class.as_view(config=self)(request, *args, group_id=group_id, **kwargs)

    def get_urls(self):
        """Builds a list of urls"""
        return [
            path("", self.get_home_view, name="group_general"),
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
    url_keyword = "settings"
    name = "Settings"
    icon_class = "fas fa-cog"
    url_name = "settings:settings_home"
    order_value = 999
    namespace = "settings"

    def get_urls(self):
        """Builds a list of urls"""
        urls = [
            path("", AssociationGroupSettingsView.as_view(config=self), name="settings_home"),
            *settings_options_registry.urls(self),
        ]
        return urls

    def get_options(self, association_group):
        return settings_options_registry.get_options(association_group)

    def check_group_access(self, association_group):
        if not super(AssociationGroupSettingsConfig, self).check_group_access(association_group):
            return False
        return bool(self.get_options(association_group))
