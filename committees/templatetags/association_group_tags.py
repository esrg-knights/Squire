from django import template

from committees.utils import user_in_association_group

register = template.Library()


@register.filter
def is_in_group(user, group):
    return user_in_association_group(user, group)
