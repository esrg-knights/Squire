import datetime

from django import forms
from django.forms import ModelForm, ValidationError
from django.utils import timezone

from core.forms import MarkdownForm
from committees.models import AssociationGroup

from activity_calendar.constants import ActivityType, SlotCreationType, ActivityStatus
from activity_calendar.models import Activity, ActivityMoment
from activity_calendar.forms import ActivityMomentFormMixin
from activity_calendar.committee_pages.utils import get_meeting_activity, create_meeting_activity
from activity_calendar.widgets import BootstrapDateTimePickerInput


__all__ = [
    "CreateActivityMomentForm",
    "AddMeetingForm",
    "EditMeetingForm",
    "MeetingRecurrenceForm",
    "CancelMeetingForm",
    "EditCancelledMeetingForm",
]


class CreateActivityMomentForm(ActivityMomentFormMixin, MarkdownForm):
    class Meta:
        model = ActivityMoment
        fields = [
            "recurrence_id",
            "local_title",
            "local_description",
            "local_promotion_image",
            "local_location",
            "local_max_participants",
            "local_subscriptions_required",
            "local_slot_creation",
            "local_private_slot_locations",
        ]

    placeholder_detail_title = "Base Activity %s"

    def __init__(self, *args, activity=None, **kwargs):
        # Require that an instance is given as this contains the required attributes parent_activity and recurrence_id
        if activity is None:
            raise KeyError("Activity was not given")
        super(CreateActivityMomentForm, self).__init__(*args, **kwargs)

        self.instance.parent_activity = activity
        self.prep_placeholders()

        self.instance.recurrence_id = timezone.now() + datetime.timedelta(days=7)
        self.fields["recurrence_id"].initial = self.instance.recurrence_id


class AddMeetingForm(ModelForm):
    class Meta:
        model = ActivityMoment
        fields = [
            "local_start_date",
            "local_location",
        ]
        widgets = {
            "local_start_date": BootstrapDateTimePickerInput(),
        }
        labels = {
            "local_start_date": "Start date and time",
        }

    def __init__(self, *args, association_group: AssociationGroup = None, **kwargs):
        if association_group is None:
            raise KeyError("Association group was not given")
        self.association_group = association_group
        super(AddMeetingForm, self).__init__(*args, **kwargs)

        self.instance.parent_activity = self.get_parent_activity()

        self.fields["local_start_date"].required = True

    def clean_local_start_date(self):
        if self.instance.id is None:
            if self.get_parent_activity().get_occurrence_at(self.cleaned_data["local_start_date"]):
                raise ValidationError(message="A meeting already exists for the given moment", code="already-exists")
        return self.cleaned_data["local_start_date"]

    def get_parent_activity(self):
        activity = get_meeting_activity(association_group=self.association_group)
        if activity is None:
            activity = create_meeting_activity(self.association_group)
        return activity

    def save(self, commit=True):
        self.set_default_values()
        return super(AddMeetingForm, self).save(commit=commit)

    def set_default_values(self):
        self.instance.recurrence_id = self.cleaned_data["local_start_date"]
        if not self.instance.local_location:
            self.instance.local_location = "-"


class EditMeetingForm(ModelForm):
    class Meta:
        model = ActivityMoment
        fields = [
            "local_description",
            "local_location",
        ]
        labels = {
            "local_description": "Information",
            "local_location": "Location",
        }

    def save(self, commit=True):
        local_location = self.cleaned_data["local_location"]
        if not self.instance.is_part_of_recurrence and not local_location:
            self.instance.local_location = "-"

        return super(EditMeetingForm, self).save(commit=commit)


class EditCancelledMeetingForm(ModelForm):
    class Meta:
        model = ActivityMoment
        fields = []

    def __init__(self, *args, instance=None, **kwargs):
        if not instance.is_cancelled:
            raise KeyError("The meeting was not cancelled")
        super(EditCancelledMeetingForm, self).__init__(*args, instance=instance, **kwargs)

    def save(self, commit=True):
        self.instance.status = ActivityStatus.STATUS_NORMAL
        self.instance.save()


class MeetingRecurrenceForm(ModelForm):
    class Meta:
        model = Activity
        fields = ["recurrences", "start_date"]


class CancelMeetingForm(ModelForm):
    full_delete = forms.BooleanField(
        label="Delete entirely", help_text="Checking this will delete the meeting entirely", required=False
    )

    class Meta:
        model = ActivityMoment
        fields = ["full_delete"]

    def __init__(self, *args, instance=None, **kwargs):
        if instance.is_cancelled:
            raise KeyError("The meeting was already cancelled")
        super(CancelMeetingForm, self).__init__(*args, instance=instance, **kwargs)

        if self.instance.is_part_of_recurrence:
            self.fields["full_delete"].disabled = True
            self.fields["full_delete"].help_text = "option disabled. Recurrent meetings can not be deleted"

    def save(self, commit=True):
        if self.cleaned_data["full_delete"]:
            self.instance.status = ActivityStatus.STATUS_REMOVED
        else:
            self.instance.status = ActivityStatus.STATUS_CANCELLED
        self.instance.save()


class GroupMeetingSettingsForm(ModelForm):
    class Meta:
        model = Activity
        fields = ["title", "description"]

    def __init__(self, *args, instance=None, **kwargs):
        instance = get_meeting_activity(instance)
        super(GroupMeetingSettingsForm, self).__init__(*args, instance=instance, **kwargs)
