from django import template
from django.urls import reverse
from django.conf import settings

from django.templatetags.static import StaticNode

register = template.Library()

##################################################################################
# Template Tag that builds an absolute URI
# @since 28 APRIL 2023
##################################################################################

@register.simple_tag(takes_context=True)
def abs_url(context, view_name: str, from_string=False, **kwargs):
    """
    Constructs an absolute url based on the viewname
    :param context: The view context
    :param view_name: The url view_name (e.g. core:register)
    :param from_string: Boolean, whether view_name is a local string instead. Use this to change an already formed url
    to an absolute url string. (e.g. "core/register")
    :param kwargs: Keyword arguments
    :return:
    """
    if from_string:
        if not view_name.startswith('/'):
            view_name = '/' + view_name
        return f"https://{context['site'].domain}{view_name}"
    else:
        url = reverse(view_name, kwargs=kwargs)
        return f"https://{context['site'].domain}{url}"


