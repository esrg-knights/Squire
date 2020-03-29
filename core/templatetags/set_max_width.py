from django import template

register = template.Library()

##################################################################################
# Template Filter that sets the max-width of a field
# @since 27 MAR 2020
##################################################################################

@register.filter
def set_max_width(field, width):
    if width >= 0:
        return field.as_widget(attrs={'style': f'max-width: {width}px;'})
    return field.as_widget()
