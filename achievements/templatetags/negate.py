from django import template

register = template.Library()

##################################################################################
# Template Tag that negates a value
# @since 11 MAR 2020
##################################################################################


@register.filter
def negate(value):
    return -value
