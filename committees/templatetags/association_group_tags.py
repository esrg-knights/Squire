from django import template

register = template.Library()


@register.filter
def is_in_group(user, group):
    return user.groups.filter(id=group.id).exists()
