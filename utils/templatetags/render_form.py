from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()

##################################################################################
# Template Tag that renders a complete form even with a possible automatic submit button
# @since SEPT 2020
##################################################################################

submit_text_default = "Submit"
submit_class_default = "btn btn-default"

@register.inclusion_tag('utils/snippets/form_total.html', takes_context=True)
def render_form(context, form=None, has_submit_button=True, uses_file_field=False, **kwargs):
    """
    Renders a complete form with all fields with bootstrap defined styling
    :param context: The render context, given automatically
    :param form: the form that needs to be rendered. If None given defaults to context['form']
    :param has_submit_button: Whether a submit button needs to be displayed
    :param uses_file_field: Boolean whether a filefield is in the form. Changes enctype if true
    :param kwargs: Other defining kwargs. Check the code for what is possible
    :return: A fully rendered form
    """
    if form is None:
        form = context['form']

    return {
        'request': context['request'],
        'form': form,
        'form_id': kwargs.get('id', None),
        'form_action': kwargs.get('action', None),
        'form_method': kwargs.get('method', None),
        'form_class': kwargs.get('form_class', None),
        'form_enctype': "multipart/form-data" if uses_file_field else None,
        'submit_display': has_submit_button,
        'submit_class': kwargs.get('submit_class', submit_class_default),
        'submit_text': _(kwargs.get('submit_text', submit_text_default))
    }
