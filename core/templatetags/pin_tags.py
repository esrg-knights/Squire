from django import template
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string

from core.pin_models import Pin

register = template.Library()


##################################################################################
# Template Tags used for pins
# @since 25 NOV 2021
##################################################################################

@register.filter
def get_pins(user):
    """ Returns a Queryset containing the pins accessible to the given user """
    return Pin.objects.for_user(user, limit_to_highlights=True)

@register.simple_tag(takes_context=True)
def render_pin(context, pin, short=True):
    """ Renders a pin """
    template = pin.get_pin_highlight_template() if short else pin.get_pin_base_template()
    return render_to_string(template, {
        'pin': pin,
        'context': context,
    })

@register.inclusion_tag("core/pins/pinnable_form.html", takes_context=True)
def pinnable_form(context, pinnable_prefix, btn_classes=""):
    """
        Renders a form to (un)pin an item in this View. This View must
        inherit `PinnablesMixin` in order for this to work.

        - `obj` is the object that should be (un)pinned. Only its ContentType is used here.
        - `index` is the index of the object as provided in `PinnablesMixin.get_pinnable_objects()`
            This is used to identify the correct form.
        - `btn_classes` can be used to attach extra CSS classes to the (un)pin button
    """
    pinnable_form = context.get(pinnable_prefix, None)

    if pinnable_form is None: # pragma: no cover
        raise ImproperlyConfigured(f"Form with prefix {pinnable_prefix} does not exist in this context.")

    return {
        'pinnable_form': pinnable_form,
        'do_pin': pinnable_form.initial['do_pin'],
        'btn_classes': btn_classes,
    }
