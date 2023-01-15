from django.template.loader import get_template
from django.urls import path, include
from django.utils.safestring import mark_safe


class OptionsRegistry:
    """ Registry for all different settings and whether the current associationgroup has access """

    _setting_options = []

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
        options = []
        for settings_option in self._setting_options:
            if settings_option.check_group_access(association_group):
                options.append(settings_option)
        return options

    def can_access(self, association_group, option):
        return option in self.get_options(association_group)


settings = OptionsRegistry()

class SettingsOptionBase:
    name = None
    title = None
    url_keyword  = ''
    template_name = None
    group_type_required = []
    group_permission_required = None

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

    def check_group_access(self, association_group):
        if self.group_type_required and association_group.type not in self.group_type_required:
            return False
        if self.group_permission_required:
            # Todo Implement permission check from utils in pull #291
            pass
        return True

    def get_urls(self, config):
        url_key = f'{self.url_keyword}/' if self.url_keyword else ''
        return path(url_key, include(self.build_url_pattern(config)))

    def build_url_pattern(self, config):
        """ Builds a list of urls """
        raise NotImplementedError(f"Urls not implemented on {self.__class__.__name__}")
