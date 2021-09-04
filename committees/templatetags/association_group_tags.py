from django import template

from committees.config import get_all_configs_for_group
from committees.utils import user_in_association_group

register = template.Library()


@register.filter
def is_in_group(user, group):
    return user_in_association_group(user, group)


@register.filter
def get_group_tabs(association_group):
    tabs = []
    for committee_config in get_all_configs_for_group(association_group):
        tabs.append(committee_config.get_tab_data())
    return tabs
