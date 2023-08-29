from django import template

from committees.committee_pages.options import SettingsOptionBase
from committees.committeecollective import registry


__all__ = ["render_options", "get_absolute_url", "get_accessible_configs"]

register = template.Library()


@register.simple_tag(takes_context=True)
def render_options(context, setting_option: SettingsOptionBase):
    return setting_option.render(association_group=context.get("association_group"))


@register.filter
def get_accessible_configs(association_group):
    accessible_configs = []
    for config in registry.configs:
        if config.check_group_access(association_group):
            accessible_configs.append(config)
    return accessible_configs


@register.filter
def get_absolute_url(config, association_group):
    return config.get_absolute_url(association_group)
