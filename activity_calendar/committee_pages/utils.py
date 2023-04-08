from datetime import datetime, timedelta
from django.utils.timezone import get_current_timezone

from activity_calendar.models import Activity, ActivityMoment
from activity_calendar.constants import ActivityType
from committees.models import AssociationGroup


def get_meeting_activity(association_group: AssociationGroup):
    """Returns the meeting activity for the given group instance"""
    meeting = association_group.activity_set.filter(type=ActivityType.ACTIVITY_MEETING).first()
    if meeting is None:
        return create_meeting_activity(association_group)
    else:
        return meeting


def create_meeting_activity(association_group: AssociationGroup):
    activity = Activity.objects.create(
        title=f"{association_group.name} meeting",
        type=ActivityType.ACTIVITY_MEETING,
        start_date=datetime.fromtimestamp(1, tz=get_current_timezone()),
        end_date=datetime.fromtimestamp(1, tz=get_current_timezone()) + timedelta(hours=1),
    )
    activity.organisers.set([association_group])
    return activity
