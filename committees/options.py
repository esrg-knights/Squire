from django.contrib.auth.models import Permission
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import get_template
from django.urls import path, include, reverse_lazy

from utils.auth_utils import get_perm_from_name

from committees.views import BaseSettingsUpdateView


class OptionsRegistry:
    """Registry for all different settings and whether the current associationgroup has access"""

    def __init__(self):
        self._setting_options = []

    def register(self, options_class):
        """Registers an option to the settings config"""
        assert issubclass(options_class, SettingsOptionBase)
        if options_class not in self._setting_options:
            self._setting_options.append(options_class())

    def urls(self, config):
        """Return the entire list of urls"""
        urls = []
        for setting_option in self._setting_options:
            urls.append(setting_option.get_urls(config))
        return urls

    def get_options(self, association_group):
        """Returns a list of availlable setting option classes that are availlable for the given association_group"""
        options = []
        for settings_option in self._setting_options:
            if settings_option.check_option_access(association_group):
                options.append(settings_option)
        return options


settings_options_registry = OptionsRegistry()


class SettingsOptionBase:
    """
    Forms the base configuration options for a settings module that can hook into the options registry
    This is used by the settings config
    name: The name of the config
    url_keyword: keyword used in the url to differentiate this setting from others
    url_name: Name of the url path to link to
    template_name: Name of the template used in the settings view
    group_type_required: list of group types that should adhere to this tab.
    group_permission_required: required permission for this option to show up.

    Note: To reverse an url, use committees:settings:_your_url_name_
    """

    name = None
    order = 10
    url_keyword = ""
    url_name = None
    option_template_name = None
    group_type_required = []
    group_requires_permission = None

    @property
    def home_url_name(self):
        """Returns the full url name to be used in the Django reverse funciton"""
        return f"committees:settings:{self.url_name}"

    def render(self, association_group):
        """Renders a block displayed in the settings page"""
        if self.option_template_name is None:
            return ""

        context = self.get_context_data(association_group)
        template = get_template(self.option_template_name)
        rendered_result = template.render(context)
        return rendered_result

    def get_context_data(self, association_group):
        return {"association_group": association_group}

    def check_option_access(self, association_group):
        if isinstance(self.group_type_required, str):
            self.group_type_required = [self.group_type_required]
        if self.group_type_required and association_group.type not in self.group_type_required:
            return False
        if self.group_requires_permission:
            try:
                perm = get_perm_from_name(self.group_requires_permission)
            except Permission.DoesNotExist:
                raise ImproperlyConfigured(
                    f"{self.__class__.__name__} is configured incorrectly. "
                    f"{self.group_requires_permission} is not a valid permission."
                )
            else:
                if (
                    not perm.group_set.filter(associationgroup=association_group).exists()
                    and not perm.associationgroup_set.filter(id=association_group.id).exists()
                ):
                    return False
        return True

    def get_urls(self, config):
        url_key = f"{self.url_keyword}/" if self.url_keyword else ""
        return path(url_key, include(self.build_url_pattern(config)))

    def build_url_pattern(self, config):
        """Builds a list of urls"""
        raise NotImplementedError(f"Urls not implemented on {self.__class__.__name__}")


class SimpleFormSettingsOption(SettingsOptionBase):
    """
    A simple option resolving just one form
    display_title: The title displayed on the top the form page
    display_text: The text displayed on the form page
    option_template_name: The template name for the option
    form_template_name: The template name for the option
    option_form_class: The form class that this settings option resolves
    """

    display_title = ""
    display_text = ""
    form_template_name = "committees/committee_pages/group_settings_edit.html"
    option_form_class = None
    url_name = None

    def __init__(self):
        super(SimpleFormSettingsOption, self).__init__()
        if self.url_name is None:
            self.url_name = self.__class__.__name__

    def get_context_data(self, association_group):
        context = super(SimpleFormSettingsOption, self).get_context_data(association_group=association_group)
        context.update(
            {
                "settings_url": reverse_lazy(
                    f"committees:settings:{self.url_name}", kwargs={"group_id": association_group}
                ),
            }
        )
        return context

    def get_view_class(self):
        return type(
            f"{self.option_form_class.__name__}OptionView",
            (BaseSettingsUpdateView,),
            {
                "form_class": self.option_form_class,
                "template_name": self.form_template_name,
            },
        )

    def build_url_pattern(self, config):
        return [
            path("", self.get_view_class().as_view(config=config, settings_option=self), name=self.url_name),
        ]
