from django import template

from nextcloud_integration.models import NCFile

register = template.Library()


@register.filter
def has_edit_access(folder, user):
    return True
