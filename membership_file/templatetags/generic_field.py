from django import template
from django.utils.html import format_html
from .field_label import field_label
from typing import Dict # NB: Should be OrderedDict, but this was only introduced in Python 3.7 and we're running 3.5

register = template.Library()

##################################################################################
# Template Tag that creates standard form inputs based on a template
# @author E.M.A. Arts
# @since 05 FEB 2020
##################################################################################

@register.inclusion_tag('membership_file/form_field.html')
def generic_field(*args):
    return {'fields': args}
