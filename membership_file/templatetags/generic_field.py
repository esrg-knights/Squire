from django import template

register = template.Library()

##################################################################################
# Template Tag that creates standard form inputs based on a template
# @since 05 FEB 2020
##################################################################################

@register.inclusion_tag('membership_file/form_field.html')
def generic_field(*args):
    return {'fields': args}
