from datetime import datetime, timedelta
from django.utils.timezone import get_current_timezone

from activity_calendar.models import Activity, ActivityMoment
from activity_calendar.constants import *
from committees.models import AssociationGroup


def get_meeting_activity(association_group:AssociationGroup):
    """ Returns the meeting activity for the given group instance """
    return association_group.activity_set.filter(type=ACTIVITY_MEETING).last()

def create_meeting_activity(association_group:AssociationGroup):
    activity = Activity.objects.create(
        title = f"Meeting for group {association_group.name}",
        is_public = False,
        type=ACTIVITY_MEETING,
        start_date=datetime.fromtimestamp(1, tz=get_current_timezone()),
        end_date=datetime.fromtimestamp(1, tz=get_current_timezone()) + timedelta(hours=1)
    )
    activity.organisers.set([association_group])
    return activity