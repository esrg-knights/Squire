from django.template.loader import get_template
from django.urls import path, include

from committees.models import AssociationGroup


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
    """
    Forms the base configuration options for a settings module that can hook into the options registry
    This is used by the settings config
    name: The name of the config
    title: The title presented to the user
    url_keyword: keyword used in the url to differentiate this setting from others
    template_name: Name of the template used in the settings view
    group_type_required: list of group types that should adhere to this tab.
    group_permission_required: required permission for this option to show up.
    """
    name = None
    title = None
    url_keyword  = ''
    option_template_name = None
    group_type_required = []
    group_permission_required = None

    def render(self, association_group):
        """ Renders a block displayed in the settings page """
        if self.option_template_name is None:
            return ''

        context = self.get_context_data(association_group)
        template = get_template(self.option_template_name)
        rendered_result = template.render(context)
        return rendered_result

    def get_context_data(self, association_group):
        return {'association_group': association_group}

    def check_group_access(self, association_group):
        if isinstance(self.group_type_required, str):
            self.group_type_required = [self.group_type_required]
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


class SimpleFormSettingsOption(SettingsOptionBase):
    option_template_name = "committees/snippets/simple_settings_snippet.html"
    option_form_class = None
    resolver_name = None

    def get_form_class(self):
        return self.option_form_class

    def build_form_view(self, ):
        def render_form(request, *args, group_id: AssociationGroup, **kwargs):
            pass

    def build_url_pattern(self, config):
        return [
            path('', self.build_form_view(), name=self.resolver_name),
        ]
