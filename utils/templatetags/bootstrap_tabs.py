import urllib

from django import template
from django.utils.html import format_html
from django.urls import reverse

register = template.Library()


@register.simple_tag
def bootstrap_tab(text, active, active_value=None, url=None, url_name=None, **url_kwargs):
    """ Renders a bootstrap tab with the given url only when active is false"""

    if active_value:
        # Add a selector option to the active value
        if active_value != active:
            active = False

    if active:
        return format_html(
            '<a class="nav-link active">{text}</a>',
            text=text
        )
    else:
        if url_name:
            url = reverse(viewname=url_name, kwargs=url_kwargs)
        elif url is None:
            raise KeyError("Either a url_name or url must be given")

        return format_html(
            '<a class="nav-link" href="{url}">{text}</a>',
            url=url,
            text=text
        )
