import urllib

from django import template
from django.contrib.auth.models import User, Group

register = template.Library()

from membership_file.util import user_to_member


@register.filter
def get_owned_by(item, owner):
    """ A tag that determines for a given item if its owned by a given user"""
    if isinstance(owner, Group):
        return item.ownerships.filter(group=owner)
    if isinstance(owner, User):
        member = user_to_member(owner).get_member()
        if member:
            return item.ownerships.filter(member=member)
        else:
            return item.ownerships.none()
