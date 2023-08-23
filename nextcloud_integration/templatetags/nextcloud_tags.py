from django import template

register = template.Library()


@register.filter
def has_edit_access(user, folder=None):
    return user.has_perm("nextcloud_integration.change_squirenextcloudfolder")


@register.filter
def has_sync_access(user):
    return user.has_perm("nextcloud_integration.sync_squirenextcloudfile")
