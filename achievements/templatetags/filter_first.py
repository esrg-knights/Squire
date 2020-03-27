from django import template

register = template.Library()

##################################################################################
# Template Tag that filters out the first X elements of a list
# @since 11 MAR 2020
##################################################################################


@register.filter
def filter_first(list, x):
    return list[:x]
