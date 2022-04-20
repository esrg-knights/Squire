from django.template.loader import get_template
from django.urls import path, include
from django.utils.safestring import mark_safe


from committees.models import AssociationGroup
from committees.committee_pages.views import *


class SettingsRegistry:
    """ Registry for all different settings and whether the current associationgroup has access """

    _setting_access = []
    _setting_options = []

    def add_setting_access(cls, settings_class):
        """ Adds an option access block to the config """
        assert issubclass(settings_class, SettingAccessBase)
        if settings_class not in cls._setting_access:
            cls._setting_access.append(settings_class())

    def add_setting_option(cls, options_class):
        """ Adds an options block to the config """
        assert issubclass(options_class, SettingsOptionBase)
        if options_class not in cls._setting_options:
            cls._setting_options.append(options_class())

    def urls(self, config):
        """ Return the entire list of urls """
        urls = []
        for setting_option in self._setting_options:
            urls.append(setting_option.get_urls(config))
        return urls

    def get_options(self, association_group):
        """ Returns a list of availlable setting option classes that are availlable for the given association_group """
        access_blocks = []
        for access_class in self._setting_access:
            if access_class.check_validity(association_group):
                access_blocks.append(access_class)

        options = []
        for setting_option in self._setting_options:
            for access_class in access_blocks:
                if access_class.has_access_to_option(setting_option):
                    print('C - {setting_option} - {access_class}')
                    options.append(setting_option)
                    continue
        return options

    def can_access(self, association_group, option):
        print(option)
        print(self.get_options(association_group))
        return option in self.get_options(association_group)


settings = SettingsRegistry()


class SettingsOptionBase:
    name = None
    title = None
    url_keyword  = ''
    template_name = None

    def render(self, association_group):
        """ Renders a block displayed in the settings page """
        if self.template_name is None:
            return ''

        context = self.get_context_data(association_group)
        template = get_template(self.template_name)
        rendered_result = template.render(context)
        return mark_safe(rendered_result)

    def get_context_data(self, association_group):
        return {'association_group': association_group}

    def get_urls(self, config):
        url_key = f'{self.url_keyword}/' if self.url_keyword else ''
        return path(url_key, include(self.build_url_pattern(config)))

    def build_url_pattern(self, config):
        """ Builds a list of urls """
        raise NotImplementedError(f"Urls not implemented on {self.__class__.__name__}")


class InfoOptions(SettingsOptionBase):
    name = 'home_info_text'
    title = "Home screen"
    template_name = "committees/committee_pages/setting_blocks/info.html"

    def build_url_pattern(self, config):
        return [path('update/', AssociationGroupUpdateView.as_view(config=config, settings_option=self), name='group_update')]


class MemberOptions(SettingsOptionBase):
    name = 'member_basic'
    title = "Members"
    template_name = "committees/committee_pages/setting_blocks/members.html"

    def build_url_pattern(self, config):
        return [
            path('members/', AssociationGroupMembersView.as_view(config=config, settings_option=self), name='group_members'),
            path('members/edit/', AssociationGroupMemberUpdateView.as_view(config=config, settings_option=self), name='group_members_edit'),
        ]


class QuicklinkOptions(SettingsOptionBase):
    name = 'quicklinks'
    title = "External sources"
    template_name = "committees/committee_pages/setting_blocks/quicklinks.html"
    def build_url_pattern(self, config):
        return [
            path('quicklinks/', include([
                path('', AssociationGroupQuickLinksView.as_view(config=config, settings_option=self), name='group_quicklinks'),
                path('edit/', AssociationGroupQuickLinksAddOrUpdateView.as_view(config=config, settings_option=self), name='group_quicklinks_edit'),
                path('<int:quicklink_id>/delete/', AssociationGroupQuickLinksDeleteView.as_view(config=config, settings_option=self), name='group_quicklink_delete'),
            ])),
        ]



settings.add_setting_option(MemberOptions)
settings.add_setting_option(QuicklinkOptions)
settings.add_setting_option(InfoOptions)


class SettingAccessBase:
    """ Defines access in accordance to the enumerable define in 'access'
    access: a list or tuple of names to availlable options
    """
    access = None

    def check_validity(self, association_group:AssociationGroup):
        """ Method that checks the validity of this block """
        return False

    def has_access_to_option(self, option):
        print(f'{self.access} - {option.name} ')
        return option.name in self.access


class BasicSettingsBlock(SettingAccessBase):
    access = ('member_basic', 'quicklinks', 'home_info_text')

    def check_validity(self, association_group):
        return association_group.type in [AssociationGroup.COMMITTEE, AssociationGroup.WORKGROUP, AssociationGroup.GUILD]


settings.add_setting_access(BasicSettingsBlock)
