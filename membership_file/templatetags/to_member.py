from django import template
from membership_file.util import user_to_member

register = template.Library()

##################################################################################
# Template Filter that transforms a User to a MemberUser
# @since 12 MAR 2020
##################################################################################

@register.filter
def to_member(user):
    return user_to_member(user)
