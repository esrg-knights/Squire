from django import template
from django.contrib.contenttypes.models import ContentType
from django.template.loader import render_to_string

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

@register.simple_tag(takes_context=True)
def render_pin(context, pin, short=True):
    """ Renders a pin """
    template = pin.get_pin_template_short() if short else pin.get_pin_template_long()
    return render_to_string(template, {
        'pin': pin,
        'context': context,
    })

@register.inclusion_tag("core/pins/pinnable_form.html", takes_context=True)
def pinnable_form(context, obj, index=0, btn_classes=""):
    """
        Renders a form to (un)pin an item in this View. This View must
        inherit `PinnablesMixin` in order for this to work.

        - `obj` is the object that should be (un)pinned. Only its ContentType is used here.
        - `index` is the index of the object as provided in `PinnablesMixin.get_pinnable_objects()`
            This is used to identify the correct form.
        - `btn_classes` can be used to attach extra CSS classes to the (un)pin button
    """
    pinnable_prefix = f"pinnable_form-{ContentType.objects.get_for_model(obj).id}-{index}"
    pinnable_form = context.get(pinnable_prefix, None)
    return {
        'pinnable_form': pinnable_form,
        'do_pin': pinnable_form.initial['do_pin'],
        'btn_classes': btn_classes,
    }
