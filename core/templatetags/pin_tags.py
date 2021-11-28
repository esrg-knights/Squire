from django import template
from activity_calendar.views import PinnableFormMixin

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


@register.inclusion_tag("core/pins/pinnable_form.html", takes_context=True)
def pinnable_form(context, pinnable_prefix=None):
    """
        Renders a form to (un)pin an item in this View. This View must
        inherit PinnableFormMixin in order for this to work.

        If there are multiple pinnables in the context, the `pinnable_prefix`
        kwarg can be used to determine which pinnable form to render.
    """
    pinnable_prefix = pinnable_prefix or PinnableFormMixin.pinnable_prefix
    return {
        'pinnable_form': context[pinnable_prefix],
    }
