import urllib

from django import template

register = template.Library()


@register.inclusion_tag('utils/snippets/paginator.html', takes_context=True)
def render_paginator(context, display_range=None, **kwargs):
    """
    Renders a complete form with all fields with bootstrap defined styling
    :param context: The render context, given automatically
    :param form: the form that needs to be rendered. If None given defaults to context['form']
    :param has_submit_button: Whether a submit button needs to be displayed
    :param kwargs: Other defining kwargs. Check the code for what is possible
    :return: A fully rendered form
    """

    current_page_number = int(context['page_obj'].number)
    total_pages = context['page_obj'].paginator.num_pages
    display_range = display_range if display_range else 2


    # Compute the maximum amount of pages displayed
    num_display_pages_below = min(current_page_number-1, display_range)
    num_display_pages_above = min(total_pages-current_page_number, display_range)

    # Make sure that a shortage on one side is corrected on the other
    correction_lower = display_range - num_display_pages_below
    correction_upper = display_range - num_display_pages_above
    num_display_pages_below = min(current_page_number-1, num_display_pages_below + correction_upper)
    num_display_pages_above = min(total_pages-current_page_number, num_display_pages_above + correction_lower)

    display_first = True if current_page_number - num_display_pages_below > 1 else False
    display_last = True if current_page_number + num_display_pages_above < total_pages else False

    start_low_at = current_page_number - num_display_pages_below
    end_high_at = current_page_number + num_display_pages_above


    return {
        # Keep the request for url purposes
        'request': context['request'],

        'current_page': current_page_number,
        'total_pages': total_pages,
        'show_range': display_range,  # The maximum amount of page-numbers above and below the current page number

        'low_pages': range(current_page_number - num_display_pages_below, current_page_number),
        'high_pages': range(current_page_number + 1, current_page_number + num_display_pages_above +1),

        'display_first': display_first,
        'display_first_with_gap': start_low_at > 2,
        'display_last': display_last,
        'display_last_with_gap': end_high_at < total_pages - 1,
    }


@register.simple_tag(takes_context=True)
def get_url_for_page(context, page_number):
    """ Updates current get params with given page number and returns it as url params """
    get_attributes = context['request'].GET.copy()
    get_attributes['page'] = page_number

    return '?'+urllib.parse.urlencode(get_attributes)
