from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()

##################################################################################
# Template Tag that creates standard form inputs based on a template
# The first half of the parameters contain the fields, whereas the second half
# contains their maximum widths (or -1 for none)
# @since 05 FEB 2020
##################################################################################

submit_text_default = "Submit"
submit_class_default = "btn btn-default"

@register.inclusion_tag('core/form_total.html', takes_context=True)
def render_form(context, form=None, has_submit_button=True, **kwargs):
    if form is None:
        form = context['form']

    return {
        'request': context['request'],
        'form': form,
        'form_id': kwargs.get('id', None),
        'form_action': kwargs.get('action', None),
        'form_method': kwargs.get('method', None),
        'form_class': kwargs.get('form_class', None),
        'submit_display': has_submit_button,
        'submit_class': kwargs.get('submit_class', submit_class_default),
        'submit_text': _(kwargs.get('submit_text', submit_text_default))
    }
