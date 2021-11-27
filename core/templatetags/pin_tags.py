from django import template
from django.utils.safestring import mark_safe

from core.pins import Pin

register = template.Library()


##################################################################################
# Template Tags used for pins
# @since 25 NOV 2021
##################################################################################

@register.filter
def get_pins(user):
    """ Returns a Queryset containing the pins accessible to the given user """
    return Pin.objects.for_user(user)
