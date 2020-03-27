from django import template

register = template.Library()

##################################################################################
# Template Filter that checks if any field in a list contains an error
# @since 27 MAR 2020
##################################################################################

@register.filter
def contains_any_error(fields):
    return len([field.errors for field, _ in fields if field.errors]) > 0
