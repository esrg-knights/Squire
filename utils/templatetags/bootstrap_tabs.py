import urllib

from django import template
from django.utils.html import format_html
from django.urls import reverse

register = template.Library()


@register.simple_tag
def bootstrap_tab(text, active, viewname, **url_kwargs):
    """ Renders a bootstrap tab with the given url only when active is false"""

    if active:
        return format_html(
            '<a class="nav-link active">{text}</a>',
            text=text
        )
    else:
        url = reverse(viewname=viewname, kwargs=url_kwargs)
        return format_html(
            '<a class="nav-link" href="{url}">{text}</a>',
            url=url,
            text=text
        )
