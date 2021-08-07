from django import template
from django.forms.widgets import Input

register = template.Library()

##################################################################################
# Template Tag that creates standard form inputs based on a template
# The first half of the parameters contain the fields, whereas the second half
# contains their maximum widths (or -1 for none)
# @since 05 FEB 2020
##################################################################################

@register.inclusion_tag('utils/snippets/form_field.html')
def generic_field(*args):
    fields = list(zip(args[:len(args)//2], args[len(args)//2:]))
    only_checkboxes = True

    # Ensure the correct bootstrap classes are added to input fields
    for boundfield, _ in fields:
        multi_or_single_widget = boundfield.field.widget
        # If the widget is a multi-widget, apply css to all its widgets
        widgets = getattr(multi_or_single_widget, 'widgets', [multi_or_single_widget])

        # Update the css classes of all widgets and apply bootstrap
        for widget in widgets:
            old_classes = widget.attrs.get('class', '')

            input_type = getattr(widget, 'input_type', None)
            if input_type == 'checkbox':
                widget.attrs['class'] = old_classes + ' form-check-input'
            else:
                widget.attrs['class'] = old_classes + ' form-control'
                only_checkboxes = False

    return {
        'fields': fields,
        'only_checkboxes': only_checkboxes,
    }
