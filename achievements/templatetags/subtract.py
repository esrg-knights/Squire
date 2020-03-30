from django import template

register = template.Library()

##################################################################################
# Template Tag that subtracts values
# Based on django's add filter
# @since 27 MAR 2020
##################################################################################

@register.filter(is_safe=False)
def subtract(value, arg):
    """Subtract the arg from the value."""
    return int(value) - int(arg)
