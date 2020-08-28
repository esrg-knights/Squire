from django import template
from django.forms.widgets import Input

register = template.Library()

##################################################################################
# Template Tag that creates standard form inputs based on a template
# The first half of the parameters contain the fields, whereas the second half
# contains their maximum widths (or -1 for none)
# @since 05 FEB 2020
##################################################################################

@register.inclusion_tag('core/form_field.html')
def generic_field(*args):
    fields = list(zip(args[:len(args)//2], args[len(args)//2:]))

    # Ensure the correct bootstrap classes are added to input fields
    for boundfield, _ in fields:
        multi_or_single_widget = boundfield.field.widget
        widgets = [multi_or_single_widget]
        if hasattr(multi_or_single_widget, 'widget'):
            # Widget is a multi-widget, apply css to all subwidgets
            widgets = multi_or_single_widget.widgets

        # Update the css classes of all widgets and apply bootstrap
        for widget in widgets:
            old_classes = ''
            if 'class' in widget.attrs:
                old_classes = widget.attrs['class'] + ' '
            widget.attrs['class'] = old_classes + 'form-control'

    return {
        'fields': fields,
    }
