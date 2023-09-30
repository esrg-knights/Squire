from django import template
from django.http.request import HttpRequest
from django.templatetags.static import StaticNode

register = template.Library()

##################################################################################
# Template Tag that builds an absolute URI
# @since 17 MAR 2021
##################################################################################


@register.simple_tag
def build_absolute_uri(request: HttpRequest, location=None) -> str:
    return request.build_absolute_uri(location)


@register.simple_tag
def webcal_uri(request: HttpRequest, location=None):
    return build_absolute_uri(request, location).replace("https://", "webcal://").replace("http://", "webcal://")


@register.simple_tag
def build_absolute_image_uri(request: HttpRequest, image):
    return request.build_absolute_uri(StaticNode.handle_simple(image))
