from django.core.exceptions import ImproperlyConfigured
from django.forms.boundfield import BoundField
from core.widgets import ImageUploadMartorWidget
from django import template

register = template.Library()

##################################################################################
# Template Tag to render fields according to a template
# @since 05 FEB 2020
##################################################################################

@register.inclusion_tag('utils/snippets/form_field.html')
def generic_field(*args):
    """
    Creates standard form inputs based on a predefined template.
    The first half of the parameters contain the fields, whereas
    the second half contains their maximum widths (or -1 for none)
    """
    # Change the input parameters to (field, max_field_length) tuples
    fields = list(zip(args[:len(args)//2], args[len(args)//2:]))
    only_checkboxes = True
    is_markdown = False

    # Ensure the correct bootstrap classes are added to input fields
    for boundfield, _ in fields:
        # Catch errors made when passing wrong parameters, which can happen during development
        if not isinstance(boundfield, BoundField):
            raise ImproperlyConfigured('Passed a wrong parameter to generic_field; exepected a Field but got %s.' % str(boundfield))

        multi_or_single_widget = boundfield.field.widget

        if multi_or_single_widget is not None and isinstance(multi_or_single_widget, ImageUploadMartorWidget):
            # It does not make sense to place a Markdown-editor in line with other fields
            if len(fields) > 1:
                raise ImproperlyConfigured(
                    'Cannot include field %s with a Markdown-widget together with other fields.'
                    % boundfield.label
                )
            is_markdown = True
            # No need to add bootstrap classes; Martor doesn't need any
            break

        # If the widget is a multi-widget, apply css to all its widgets
        widgets = getattr(multi_or_single_widget, 'widgets', [multi_or_single_widget])

        # Update the css classes of all widgets and apply bootstrap
        for widget in widgets:
            old_classes = widget.attrs.get('class', '')

            input_type = getattr(widget, 'input_type', None)
            if input_type == 'checkbox':
                # Checkbox bootstrap form class
                widget.attrs['class'] = old_classes + ' form-check-input'
            else:
                # Input bootstrap form class
                widget.attrs['class'] = old_classes + ' form-control'
                only_checkboxes = False
    return {
        'fields': fields,
        'only_checkboxes': only_checkboxes,
        'is_markdown': is_markdown,
    }
