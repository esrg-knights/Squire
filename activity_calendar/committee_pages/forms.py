
from django import forms
from django.forms import ModelForm, Form
from django.forms.widgets import HiddenInput
from django.utils.timesince import timeuntil
from django.utils.translation import gettext_lazy as _

from core.forms import MarkdownForm
from core.widgets import ImageUploadMartorWidget

from activity_calendar.models import ActivityMoment


class CreateActivityMomentForm(MarkdownForm):
    class Meta:
        model = ActivityMoment
        fields = [
            'recurrence_id',
            'local_title', 'local_description',
            'local_promotion_image',
            'local_location',
            'local_max_participants', 'local_subscriptions_required',
            'local_slot_creation', 'local_private_slot_locations'
        ]

    placeholder_detail_title = "Base Activity %s"

    def __init__(self, *args, activity=None, **kwargs):
        # Require that an instance is given as this contains the required attributes parent_activity and recurrence_id
        if activity is None:
            raise KeyError("Activity was not given")
        super(CreateActivityMomentForm, self).__init__(*args, **kwargs)
        self.instance.parent_activity = activity

        # Set a placeholder on all fields
        for key, field in self.fields.items():
            attr_name = key[len('local_'):]

            if isinstance(field.widget, forms.Select):
                # Replace the "-------" or "unknown" option for <select> fields

                # Obtain value from parent_activity.get_FOO_display() if it exists
                # Otherwise, we must be working with a true/false value from a BooleanField without custom options
                get_parent_field_display_value = getattr(self.instance.parent_activity, f"get_{attr_name}_display",
                                                         lambda: _('Yes') if getattr(self.instance.parent_activity, attr_name) else _('No')
                                                         )

                null_choice_text = _(f'{get_parent_field_display_value()} (Inherited from base activity)')

                # Replace the "-------" or "unknown" option by our newly generated text
                field.widget.choices = [
                    ((k, null_choice_text) if k in ['', 'unknown'] else (k, v)) for (k, v) in field.widget.choices
                ]
            elif isinstance(field.widget, ImageUploadMartorWidget):
                field.widget.placeholder = getattr(self.instance.parent_activity, attr_name, None)
            else:
                # Set HTML Placeholder for all other fields
                field.widget.attrs['placeholder'] = getattr(self.instance.parent_activity, attr_name, None)

