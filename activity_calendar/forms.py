from core.widgets import ImageUploadMartorWidget
from django import forms
from django.utils.formats import date_format
from django.forms import ModelForm, Form
from django.forms.widgets import HiddenInput
from django.utils.dateparse import parse_datetime
from django.utils.timesince import timeuntil
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _
from django.core.validators import ValidationError

from .models import ActivitySlot, Activity, Participant, ActivityMoment
from core.forms import MarkdownForm
from core.models import PresetImage

##################################################################################
# Defines forms related to the membership file.
# @since 28 AUG 2020
##################################################################################


__all__ = ['RegisterNewSlotForm', 'RegisterForActivitySlotForm', 'RegisterForActivityForm', 'ActivityMomentForm',
    'ActivityAdminForm', 'ActivityMomentAdminForm']


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

    def __init__(self, *args, activity=None, user=None, recurrence_id=None, activity_moment=None, **kwargs):
        assert activity is not None
        assert user is not None
        assert activity_moment is not None

        if activity.is_recurring:
            # If activity is recurring, a recurring id should be given
            assert recurrence_id is not None

        self.activity = activity
        self.recurrence_id = recurrence_id
        self.user = user
        self.activity_moment = activity_moment

        super(RegisterAcitivityMixin, self).__init__(*args, **kwargs)

        # Manually add sign_up field to fields as this is not done here automatically.
        self.fields['sign_up'] = self.sign_up

    def clean_sign_up(self):
        if 'sign_up' not in self.cleaned_data:
            raise ValidationError("Sign_up was given", code='required')
        return self.cleaned_data['sign_up']

    def clean(self):
        super(RegisterAcitivityMixin, self).clean()

        # Check the validity
        self.check_validity(self.cleaned_data)

        return self.cleaned_data

    def check_validity(self, data):
        """ Method that checks the validity in response to the given information. This is called by the clean method
        but can also be called after Form initialisation to check data prior to user interaction. Useful for checking
        if form cán be used prior to user data supply (e.g. communication in front-end.
        The data is e.g. activity, recurrence_id and user.
        Running it raises either ValidationError X or returns None
        :param data: Given data to validate to.
        :return: Raises ValidationError or returns None """
        if not self.activity_moment.is_open_for_subscriptions():
            if not self.user.has_perm('activity_calendar.can_register_outside_registration_period'):
                raise ValidationError(_("Subscriptions are currently closed."), code='closed')

        # Check if, when signing up, there is still room (because max is limited)
        if data['sign_up'] and self.activity_moment.max_participants != -1:
            # check the number of participants
            if self.activity_moment.participant_count >= self.activity_moment.max_participants:
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

    def get_base_validity_error(self):
        """
        Returns an error if present prior to user input validation. Useful to communicate reasons of denied access
        prior to filling out the form
        :return: The error in a <message, code> format or None when preliminary form data is valid
        """
        try:
            if self.is_bound:
                try:
                    self.check_validity(self.data)
                except KeyError as e:
                    # Any of the attributes was missing that is actually vital or required. As this method subverts
                    # the normal clean method to improve communication feedback prior to filling in a form this can
                    # happen. Though only in certain test-cases or when users actively start messing about
                    # (sending custom POST requests) so it defeats the purpose
                    # Either way, letting an error slip through here is fine. Clean() is the final safety net.
                    pass
            else:
                self.check_validity(self.initial)
        except ValidationError as e:
            return e
        else:
            return None


class RegisterForActivityForm(RegisterAcitivityMixin, Form):
    """
    Form for registering for normal activities that do not use multiple slots
    """

    def check_validity(self, data):
        super(RegisterForActivityForm, self).check_validity(data)

        # Subscribing directly on activities can only happen if we don't use the multiple-slots feature
        if not self.activity_moment.slot_creation == Activity.SLOT_CREATION_AUTO:
            raise ValidationError(
                _("Activity mode is incorrect. Please refresh the page."), code='invalid_slot_mode')

        # Check if user is already present in the activity
        user_subscriptions = self.activity_moment.get_user_subscriptions(self.user)
        if data.get('sign_up'):
            if user_subscriptions.exists():
                raise ValidationError(
                    _("User is already registered for this activity"),
                    code='already-registered'
                )
        # User tries to sign out but is not present on (any of the) slot(s)
        elif not user_subscriptions.exists():
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
                activity_slot = ActivitySlot.objects.create(**kwargs)

            Participant.objects.create(
                activity_slot=activity_slot,
                user=self.user,
            )
            return True
        else:
            self.activity_moment.get_user_subscriptions(self.user).delete()
            return False


class RegisterForActivitySlotForm(RegisterAcitivityMixin, Form):
    """ Form that handles registering for a specific slot """
    slot_id = forms.IntegerField(initial=-1, widget=HiddenInput)

    def check_validity(self, data):
        super(RegisterForActivitySlotForm, self).check_validity(data)

        slot_obj = self.activity_moment.get_slots().filter(
            id=data.get('slot_id', -1)
        ).first()

        # Store the slot object in the form. Its used by the view processing the form to retrieve the slot name
        self.slot_obj = slot_obj

        self.check_slot_validity(data, slot_obj)

        if data['sign_up']:
            # Can only subscribe to at most X slots
            user_subscriptions = self.activity_moment.get_user_subscriptions(user=self.user)

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
            if self.user in slot_obj.get_subscribed_users().all():
                raise ValidationError(
                    _("You are already registered for this slot"),
                    code='already-registered'
                )

            # There is still room in this slot
            if slot_obj.max_participants != -1 and slot_obj.participant_set.count() >= slot_obj.max_participants:
                raise ValidationError(
                    _("This slot is already at maximum capacity. You cannot subscribe to it."),
                    code='slot-full'
                )
        else:
            # User tries to unsubscribe from slot he/she was not registered to
            if self.user not in slot_obj.get_subscribed_users().all():
                raise ValidationError(_("You were not registered to this slot"), code='not-registered')

        return slot_obj

    def save(self):
        """ Saves the form. Returns whether the user was added (True) or removed (False) """
        slot_obj = self.activity.activity_slot_set.filter(
            recurrence_id=self.recurrence_id,
            id=self.cleaned_data.get('slot_id', -1)
        ).first()

        if self.cleaned_data['sign_up']:
            Participant.objects.create(
                activity_slot=slot_obj,
                user=self.user,
            )

            return True
        else:
            slot_obj.participant_set.filter_users_only().filter(
                user_id=self.user.id,
            ).delete()

            return False


class RegisterNewSlotForm(RegisterAcitivityMixin, ModelForm):

    class Meta:
        model = ActivitySlot
        fields = ['title', 'description', 'location', 'image', 'max_participants']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.user.has_perm('activity_calendar.can_select_slot_image'):
            # User does not have the required permissions to select an alternative slot image
            # Remove the field
            del self.fields['image']
        else:
            # Get the PrestImages available to the user
            self.fields['image'].queryset = PresetImage.objects.for_user(self.user)


    def check_validity(self, data):
        super(RegisterNewSlotForm, self).check_validity(data)

        # Is user allowed to create a slot
        if self.activity_moment.slot_creation == Activity.SLOT_CREATION_USER:
            pass
        elif self.activity_moment.slot_creation == Activity.SLOT_CREATION_STAFF \
                and self.user.has_perm('activity_calendar.can_ignore_none_slot_creation_type'):
            pass
        else:
            raise ValidationError(
                _("User is not allowed to create slots on this activity"),
                code='user-slot-creation-denied'
            )

        # Can the user (in theory) join another slot?
        if data.get('sign_up', False):
            user_subscriptions = self.activity_moment.get_user_subscriptions(user=self.user)
            if self.activity.max_slots_join_per_participant != -1 and \
                    user_subscriptions.count() >= self.activity.max_slots_join_per_participant:
                raise ValidationError(
                    _("User is already subscribed to the max number of slots (%(max_slots)s)"),
                    code='max-slots-occupied',
                    params={'max_slots': self.activity.max_slots_join_per_participant}
                )

        # Check cap for number of slots
        if not self.user.has_perm('activity_calendar.can_ignore_slot_creation_limits'):
            if self.activity.max_slots != -1 and \
                    self.activity.max_slots <= self.activity_moment.get_slots().count():
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

        # Add the user to the slot if the user wants to
        if self.cleaned_data['sign_up']:
            Participant.objects.create(
                activity_slot=slot_obj,
                user=self.user,
            )

        return slot_obj

class ActivityMomentForm(MarkdownForm):
    class Meta:
        model = ActivityMoment
        fields = ['local_title', 'local_description',
            'local_promotion_image',
            'local_location',
            'local_start_date', 'local_end_date',
            'local_max_participants', 'local_subscriptions_required',
            'local_slot_creation', 'local_private_slot_locations'
        ]

    placeholder_detail_title = "Base Activity %s"

    def __init__(self, *args, instance=None, **kwargs):
        # Require that an instance is given as this contains the required attributes parent_activity and recurrence_id
        if instance is None:
            raise KeyError("Instance of ActivityMoment was not given")
        super(ActivityMomentForm, self).__init__(*args, instance=instance, **kwargs)

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
            elif attr_name == 'start_date':
                # Special lookup for alternative start/end time
                if isinstance(self.instance.recurrence_id, str):
                    self.instance.recurrence_id = parse_datetime(self.instance.recurrence_id)
                start_humanized = date_format(localtime(self.instance.recurrence_id), "Y-m-d H:i")
                field.widget.attrs['placeholder'] = start_humanized
            elif attr_name == 'end_date':
                duration_humanized = timeuntil(self.instance.parent_activity.end_date,
                    now=self.instance.parent_activity.start_date)
                field.widget.attrs['placeholder'] = duration_humanized + " after this occurrence starts"
            else:
                # Set HTML Placeholder for all other fields
                field.widget.attrs['placeholder'] = getattr(self.instance.parent_activity, attr_name, None)

class ActivityAdminForm(MarkdownForm):
    class Meta:
        model = Activity
        fields = '__all__'

# The ActivityMoment admin form is identical to the form used in the front-end,
#   but also allows changing the parent_activity and recurrence_id
class ActivityMomentAdminForm(MarkdownForm):
    class Meta:
        model = ActivityMoment
        fields = ['parent_activity', 'recurrence_id'] + ActivityMomentForm.Meta.fields
