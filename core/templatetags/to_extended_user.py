from django import template
from core.models import ExtendedUser

register = template.Library()

##################################################################################
# Template Filter that transforms a User to an ExtendedUser
# @since 12 MAR 2020
##################################################################################

@register.filter
def to_extended_user(user):
    attrs = {field.name: getattr(user, field.name) for field in user._meta.fields}
    return ExtendedUser(**attrs)
