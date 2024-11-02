import urllib

from django import template
from django.utils.html import format_html
from django.urls import reverse

register = template.Library()


@register.inclusion_tag("utils/snippets/bootstrap_tabs.html")
def bootstrap_tabs(tabs):
    """
    Creates the tabs for bootstrap, mobile friendly
    :param tabs: A list of dictionaries with the following properties:
    'name': name to differentiate this tab with (internally)
    'verbose': displayed tab name. Can use translations
    'url': url to link to
    'url_name': url namespace to link to if url is not present
    'selected': boolean determining whether this tab is displayed as selected
    :return:
    """
    selected = None

    for tab in tabs:
        if tab.get("url", None) is None:
            if tab.get("url_name", None) is None:
                raise KeyError(f"Url on tab '{tab.get('name', '?')}' invalid. No url nor url_name was given ")
            tab["url"] = reverse(viewname=tab.get("url_name"))
        if tab.get("selected", False):
            selected = tab

    return {
        "tabs": tabs,
        "selected": selected,
    }
