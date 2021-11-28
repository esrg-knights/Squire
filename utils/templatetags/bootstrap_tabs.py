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

    print(tabs)

    for tab in tabs:
        if tab.get('url', None) is None:
            if tab.get('url_name', None) is None:
                raise KeyError(f"Url on tab '{tab.get('name', '?')}' invalid. No url nor url_name was given ")
            tab['url'] = reverse(viewname=tab.get('url_name'))
        if tab.get('selected', False):
            selected = tab

    return {
        'tabs': tabs,
        'selected': selected,
    }
