import urllib

from django import template
from django.contrib.auth.models import User, Group

register = template.Library()

from membership_file.models import Member


@register.filter
def get_owned_by(item, owner):
    """ A tag that determines for a given item if its owned by a given user"""
    if isinstance(owner, Group):
        return item.ownerships.filter(group=owner).exists()
    if isinstance(owner, Member):
        if owner:
            return item.ownerships.filter(member=owner).exists()
        else:
            return False


@register.inclusion_tag('inventory/snippets/ownership_tags.html', takes_context=True)
def render_ownership_tags(context, item):
    member = context['request'].member

    if member:
        is_owner = item.ownerships.filter(member=member, is_active=True).exists()
        is_owned_by_other_member = item.ownerships. \
            filter(is_active=True, member__isnull=False). \
            exclude(member_id=member.id).exists()
    else:
        is_owner = False
        is_owned_by_other_member = item.ownerships. \
            filter(is_active=True, member__isnull=False). \
            exists()
    return {
        'is_owner': is_owner,
        'is_owned_by_member': is_owned_by_other_member,
        'is_owned_by_knights': item.is_owned_by_association(),
    }
