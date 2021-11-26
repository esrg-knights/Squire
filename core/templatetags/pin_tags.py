from django import template
from django.utils.safestring import mark_safe

from core.pins import Pin

register = template.Library()


##################################################################################
# Template Tags used for pins
# @since 25 NOV 2021
##################################################################################

@register.simple_tag(takes_context=True)
def render_pins(context):
    """ Renders each of the pins accessible to this user as HTML, separated by a newline. """
    pin_html = []
    for pin in Pin.objects.for_user(context.request.user):
        pin_html.append(pin.render())
    return mark_safe("\n".join(pin_html))




