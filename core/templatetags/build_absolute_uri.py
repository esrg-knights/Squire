from django import template
from django.conf import settings

from django.templatetags.static import StaticNode

register = template.Library()

##################################################################################
# Template Tag that builds an absolute URI
# @since 17 MAR 2021
##################################################################################

@register.simple_tag
def build_absolute_uri(request, location=None):
    return request.build_absolute_uri(location)

@register.simple_tag
def build_absolute_image_uri(request, image):
    return request.build_absolute_uri(StaticNode.handle_simple(image))
