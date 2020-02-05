from django import template

register = template.Library()

##################################################################################
# Template Tag that adds a * character after optional form fields
# @author E.M.A. Arts
# @since 05 FEB 2020
##################################################################################


@register.simple_tag
def field_label(name, form_field):
    if form_field.field.required:
        return name + "*"
    return name
