from django import template

register = template.Library()

##################################################################################
# Template Filter that converts a number into a range of the same size, which is
# useful for loops
# @since 22 AUG 2020
##################################################################################

@register.filter(name='range')
def range_filter(number):
    return range(number)
