import datetime

from django.utils import timezone

from core.forms import MarkdownForm

from activity_calendar.models import ActivityMoment
from activity_calendar.forms import ActivityMomentFormMixin


class CreateActivityMomentForm(ActivityMomentFormMixin, MarkdownForm):
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
        self.prep_placeholders()

        self.instance.recurrence_id = timezone.now() + datetime.timedelta(days=7)
        self.fields['recurrence_id'].initial = self.instance.recurrence_id

