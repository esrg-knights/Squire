from django import template

register = template.Library()

##################################################################################
# Template Tag that creates standard form inputs based on a template
# The first half of the parameters contain the fields, whereas the second half
# contains their maximum widths (or -1 for none)
# @since 05 FEB 2020
##################################################################################

@register.inclusion_tag('membership_file/form_field.html')
def generic_field(*args):
    return {
        'fields': list(zip(args[:len(args)//2], args[len(args)//2:])),
    }
