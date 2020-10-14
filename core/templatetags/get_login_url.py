from django import template
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.http import QueryDict
from django.contrib.auth.views import redirect_to_login

register = template.Library()

##################################################################################
# Template Tag that creates an url to a login page with the redirect set to the current page
# @since SEPT 2020
##################################################################################


@register.simple_tag(takes_context=True)
def get_login_url(context, redirect_field_name="next"):
    """ Creates a login url that redirects after completion to the current page """

    # This code originates from django.contrib.auth.views import redirect_to_login
    # with minor adjustments to cut down the amount of mix-ups
    login_url_parts = list(urlparse(settings.LOGIN_URL))

    querystring = QueryDict(login_url_parts[4], mutable=True)
    querystring[redirect_field_name] = context['request'].build_absolute_uri()
    login_url_parts[4] = querystring.urlencode(safe='/')

    return urlunparse(login_url_parts)