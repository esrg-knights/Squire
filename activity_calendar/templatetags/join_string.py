from django import template

register = template.Library()

##################################################################################
# Template Tag that joins an array of strings.
# @since 31 AUG 2020
##################################################################################

@register.simple_tag
def join_string(strings):
    return ', '.join(map(lambda x: str(x), strings))
