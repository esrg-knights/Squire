from django import template

from user_interaction.models import Pin
from user_interaction.pintypes import PINTYPES

register = template.Library()


##################################################################################
# Template Tags used for pins
# @since 25 NOV 2021
##################################################################################

@register.inclusion_tag("user_interaction/snippets/user_pins.html", takes_context=True)
def render_pins(context):
    """ TODO """
    pins = []
    queryset = Pin.objects.for_user(context.request.user)
    for pin in queryset:
        pintype = PINTYPES[pin.pintype](pin)
        pins.append(pintype)
    return {
        'pins': pins
    }




