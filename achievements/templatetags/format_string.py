from django import template

register = template.Library()

##################################################################################
# Template Tag that appends a * after a string if a given form field is required
# This string can be a form field name, but this is not required
# @since 05 FEB 2020
##################################################################################


@register.simple_tag
def format_string(string_to_format, *args):
    return string_to_format.format(*args)
