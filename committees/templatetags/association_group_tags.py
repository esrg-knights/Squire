from django import template

from committees.utils import user_in_association_group
from committees.models import AssociationGroup


__all__ = ["is_in_group", "is_type"]


register = template.Library()


@register.filter
def is_in_group(user, group):
    return user_in_association_group(user, group)


@register.filter
def is_type(association_group: AssociationGroup, type_name: str):
    return association_group.type == getattr(AssociationGroup, type_name)
