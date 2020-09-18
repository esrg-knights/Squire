from django import forms
from django.forms import ModelForm, Form
from django.core.exceptions import ValidationError
from django.utils.translation import gettext, gettext_lazy as _
from django.core.validators import ValidationError

from .models import ActivitySlot
from core.models import PresetImage

##################################################################################
# Defines forms related to the membership file.
# @since 28 AUG 2020
##################################################################################


# A form that allows activity-slots to be created
class ActivitySlotForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.fields['image'].queryset = PresetImage.objects.filter(selectable=True)
        self.fields['image'].label_from_instance = lambda image: image.name

    def clean_max_participants(self):
        max_participants = self.cleaned_data['max_participants']

        # Users can only create slots for at least 1 participant
        if max_participants == 0:
            raise ValidationError(['A slot cannot have 0 participants'])
        return max_participants

    def is_valid(self):
        ret = forms.Form.is_valid(self)

        # Add an 'error' class to input elements that contain an error
        for field in self.errors:
            self.fields[field].widget.attrs.update({'class': self.fields[field].widget.attrs.get('class', '') + ' alert-danger'})
        return ret

    class Meta:
        model = ActivitySlot
        fields = "__all__"


class RegisterForSlotForm(Form):

    def __init__(self, *args, slot=None, user=None, **kwargs):
        assert slot is not None
        assert user is not None
        self.slot = slot
        self.user = user
        super(RegisterForSlotForm, self).__init__(*args, **kwargs)

    def clean(self):
        if not self.slot.parent_activity.can_user_subscribe(self.user, recurrence_id=self.slot.recurrence_id):
            raise ValidationError(_("You can not subscribe to this activity"), code='invalid')

        # Can only subscribe to at most X slots
        user_subscriptions = self.slot.parent_activity.get_user_subscriptions(user=self.user, recurrence_id=self.slot.recurrence_id)


        if self.slot.parent_activity.max_slots_join_per_participant != -1 and \
                user_subscriptions.count() >= self.slot.parent_activity.max_slots_join_per_participant:
            raise ValidationError(
                _("You can not subscribe to another slot. You can only assign to at most %(max_slots) slots"),
                code='max-slots-occupied',
                params={'max_slots': self.slot.parent_activity.max_slots_join_per_participant}
            )

        slot_participants = self.slot.participants.all()

        # Can only subscribe at most once to each slot
        if self.user in slot_participants:
            raise ValidationError(_("You are already registered for this slot"), code='already-registered')

        # Slot participants limit
        if self.slot.max_participants != -1 and slot_participants.count() >= self.slot.max_participants:
            raise ValidationError(_("This slot is already at maximum capacity. You can not subscribe to it."),
                                  code='slot-full')

        return self.cleaned_data

    def get_error_message(self):
        if not self.is_valid():
            return self.non_field_errors()[0]
        else:
            return None

    def save(self):
        self.slot.participants.add(
            self.user, through_defaults={}
        )

