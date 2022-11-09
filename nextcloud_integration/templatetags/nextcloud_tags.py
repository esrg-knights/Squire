from django import template

from nextcloud_integration.models import NCFile

register = template.Library()


@register.filter
def has_edit_access(user, folder):
    return user.has_perm('nextcloud_integration.change_ncfolder')


@register.filter
def has_synch_access(user):
    return user.has_perm('nextcloud_integration.synch_ncfile')
