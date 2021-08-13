from core.widgets import ImageUploadMartorWidget
from django import template

register = template.Library()

##################################################################################
# Template Tags for fields
# @since 01 AUG 2021
##################################################################################

@register.filter
def set_max_width(field, width):
    """ Sets the maximum width (in px) of a field through the field's style-attribute """
    if width >= 0:
        return field.as_widget(attrs={'style': f'max-width: {width}px;'})
    return field.as_widget()

@register.filter
def get_required_indicator(field):
    """ Return a '*' if the field is required """
    return "*" if field.field.required else ""
