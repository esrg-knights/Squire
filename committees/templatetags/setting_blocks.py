from django import template

from committees.committee_pages.options import SettingsOptionBase


register = template.Library()


@register.simple_tag(takes_context=True)
def render_options(context, setting_option: SettingsOptionBase):
    return setting_option.render(association_group=context.get('association_group'))
