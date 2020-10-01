from django import forms
from django.forms import ModelForm, Form
from django.forms.widgets import HiddenInput
from django.utils.translation import gettext_lazy as _
from django.core.validators import ValidationError

from .models import ActivitySlot, Activity, Participant
from core.models import PresetImage

##################################################################################
# Defines forms related to the membership file.
# @since 28 AUG 2020
##################################################################################


class RegisterAcitivityMixin:
    """ A mixin that defines default behaviour for any activity registration
    Activity or slot registration has several invalidation codes:
    'invalid': general catch all for non-specified errors
    'activity-full'
    'already-registered'
    'not-registered'
    'closed'
    """
    sign_up = forms.BooleanField(required=False, widget=HiddenInput)

    def __init__(self, *args, activity=None, user=None, recurrence_id=None, **kwargs):
        assert activity is not None
        assert user is not None

        if activity.is_recurring:
            # If activity is recurring, a recurring id should be given
            assert recurrence_id is not None

        self.activity = activity
        self.recurrence_id = recurrence_id
        self.user = user

        super(RegisterAcitivityMixin, self).__init__(*args, **kwargs)

        # Manually add sign_up field to fields as this is not done here automatically. #TODO
        self.fields['sign_up'] = self.sign_up

    def clean(self):
        super(RegisterAcitivityMixin, self).clean()

        # Check the validity
        self.check_validity(self.cleaned_data)

        return self.cleaned_data

    def check_validity(self, data):
        """ Method that checks the validity in response to the given information. This compares the given data
        with the known data (activity, recurrence_id, user) and either raises a ValidationError if something is not
        correct. Or returns nothing.
        :param data: Given data to validate to.
        :return: """
        if not self.activity.are_subscriptions_open(self.recurrence_id):
            raise ValidationError(_("Subscriptions are currently closed."), code='closed')

        # Check if there is still room in the activity
        if self.activity.max_participants != -1:
            num_participants = Participant.objects.filter(
                activity_slot__parent_activity=self.activity,
                activity_slot__recurrence_id=self.recurrence_id
            ).count()
            if num_participants >= self.activity.max_participants:
                raise ValidationError(
                    _(f"This activity is already at maximum capacity."),
                    code='activity-full'
                )

    def get_first_error_code(self):
        """ Returns the error code from the first invalidation error found"""
        if self.errors:
            invalidation_errors = self.errors.as_data()
            invalidation_errors = invalidation_errors[list(invalidation_errors.keys())[0]][0]
            return invalidation_errors.code
        return None

    def get_error_message(self):
        if not self.errors:
            return self.non_field_errors()[0]
        else:
            return None

    def get_base_validity_error(self):
        """ Returns the error created by checking the basic form set-up. Used to validate user permissions """
        try:
            print("INITIAL")
            print(self.initial)
            self.check_validity(self.initial)
        except ValidationError as e:
            return e.message, e.code
        else:
            return None

class RegisterForActivityForm(RegisterAcitivityMixin, Form):
    """
    Form for registering for normal activities that do not use multiple slots
    """

    def check_validity(self, data):
        super(RegisterForActivityForm, self).check_validity(data)

        # Subscribing directly on activities can only happen if we don't use the multiple-slots feature
        if not self.activity.slot_creation == "CREATION_AUTO":
            raise ValidationError(
                _("Something went wrong. Please try again."), code='invalid')

        # Check if user is already present in the activity
        user_subscriptions = self.activity.get_user_subscriptions(self.user, self.recurrence_id)
        if data.get('sign_up'):
            if user_subscriptions.count() > 0:
                raise ValidationError(
                    _("User is already registered for this activity"),
                    code='already-registered'
                )
        # User tries to sign out but is not present on (any of the) slot(s)
        elif user_subscriptions.count() == 0:
            # User tries to unsubscribe from the activity, but there is no slot so this is not possible.
            raise ValidationError(_("User was not registered to this activity"), code='not-registered')

    def save(self):
        """ Saves the form. Returns whether the user was added (True) or removed (False) """
        if self.cleaned_data['sign_up']:
            kwargs = {
                'parent_activity': self.activity,
                'recurrence_id':self.recurrence_id,
            }
            activity_slot = ActivitySlot.objects.filter(**kwargs).first()
            if activity_slot is None:
                ActivitySlot.objects.create(**kwargs)

            activity_slot.participants.add(self.user)
            return True
        else:
            self.activity.get_user_subscriptions(self.user, self.recurrence_id).delete()
            return False


class RegisterForActivitySlotForm(RegisterAcitivityMixin, Form):
    """ Form that handles registering for a specific slot """
    slot_id = forms.IntegerField(initial=-1, widget=HiddenInput)

    def check_validity(self, data):
        super(RegisterForActivitySlotForm, self).check_validity(data)

        slot_obj = self.activity.activity_slot_set.filter(
            recurrence_id=self.recurrence_id,
            id=data.get('slot_id', -1)
        ).first()

        self.check_slot_validity(data, slot_obj)

        # Can only subscribe to at most X slots
        user_subscriptions = self.activity.get_user_subscriptions(user=self.user, recurrence_id=self.recurrence_id)

        if data['sign_up']:
            # If attempting a sign-up, test that the user is allowed to join one (additonal) slot
            if self.activity.max_slots_join_per_participant != -1 and \
                    user_subscriptions.count() >= self.activity.max_slots_join_per_participant:
                raise ValidationError(
                    _("User is already subscribed to the max number of slots (%(max_slots))"),
                    code='max-slots-occupied',
                    params={'max_slots': self.activity.max_slots_join_per_participant}
                )

    def check_slot_validity(self, data, slot_obj):
        """ Runs cleaning code for the slot related restrictions
        :param slot_obj: The slot object to validate
        :param slot_desc_name: The naming of the slot in the error. Used to replace with 'activity' on slot-less
        activities
        :return:
        """
        # Ensure slot is part of the activity
        if slot_obj is None:
            raise ValidationError(
                _("The given slot does not exist on this activity"),
                code='slot-not-found'
            )

        if data.get('sign_up', None):
            # Can only subscribe at most once to each slot
            if self.user in slot_obj.participants.all():
                raise ValidationError(
                    _("You are already registered for this slot"),
                    code='already-registered'
                )

            # There is still room in this slot
            if slot_obj.max_participants != -1 and slot_obj.participants.count() >= slot_obj.max_participants:
                raise ValidationError(
                    _("This slot is already at maximum capacity. You can not subscribe to it."),
                    code='slot-full'
                )
        else:
            # User tries to unsubscribe from slot he/she was not registered to
            if self.user not in slot_obj.participants.all():
                raise ValidationError(_("You were not registered to this slot"), code='not-registered')

        return slot_obj

    def save(self):
        """ Saves the form. Returns whether the user was added (True) or removed (False) """
        slot_obj = self.activity.activity_slot_set.filter(
            recurrence_id=self.recurrence_id,
            id=self.cleaned_data.get('slot_id', -1)
        ).first()

        if self.cleaned_data['sign_up']:
            slot_obj.participants.add(self.user)
            return True
        else:
            slot_obj.participants.remove(self.user)
            return False


class RegisterNewSlotForm(RegisterAcitivityMixin, ModelForm):

    class Meta:
        model = ActivitySlot
        fields = ['title', 'description', 'location', 'max_participants']


    def check_validity(self, data):
        super(RegisterNewSlotForm, self).check_validity(data)

        # Is user allowed to create a slot
        if self.activity.slot_creation == "CREATION_NONE" and self.user.is_superuser:
            pass
        elif self.activity.slot_creation == "CREATION_USER":
            pass
        else:
            raise ValidationError(
                _("User is not allowed to create slots on this activity"),
                code='user-slot-creation-denied'
            )

        # Can the user (in theory) join another slot?
        user_subscriptions = self.activity.get_user_subscriptions(user=self.user, recurrence_id=self.recurrence_id)
        if self.activity.max_slots_join_per_participant != -1 and \
                user_subscriptions.count() >= self.activity.max_slots_join_per_participant:
            raise ValidationError(
                _("User is already subscribed to the max number of slots (%(max_slots))"),
                code='max-slots-occupied',
                params={'max_slots': self.activity.max_slots_join_per_participant}
            )

        # Check cap for number of slots
        if self.activity.max_slots != -1 and \
                self.activity.max_slots <= self.activity.get_slots(recurrence_id=self.recurrence_id).count():
            raise ValidationError(
                _("Maximum number of slots already claimed"),
                code='max-slots-claimed'
            )

    def save(self, commit=True):
        # Set fixed attributes
        self.instance.parent_activity = self.activity
        self.instance.recurrence_id = self.recurrence_id
        self.instance.owner = self.user

        slot_obj = super(RegisterNewSlotForm, self).save(commit=commit)

        # Add the user to the slot
        slot_obj.participants.add(self.user)

        return slot_obj




