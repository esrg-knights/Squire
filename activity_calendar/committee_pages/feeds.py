from django.shortcuts import get_object_or_404
from django.urls import reverse

from committees.models import AssociationGroup

from activity_calendar.constants import *
from activity_calendar.feeds import CESTEventFeed, recurring_activities
from activity_calendar.models import Activity, ActivityMoment, Calendar

from .utils import get_meeting_activity


class MeetingCalendarFeed(CESTEventFeed):
    @property
    def file_name(self):
        return f"knights-{self.association_group.name}-calendar.ics"

    @property
    def product_id(self):
        return f"-//Squire//{self.association_group.name} Meeting Calendar//EN"

    @property
    def calendar_title(self):
        return f"{self.association_group.name} meetings agenda - Knights"

    @property
    def calendar_description(self):
        return f"Calendar for meetings for {self.association_group.name}. Provided by Squire, the Knights WebApp"

    def item_link(self, item):
        # The local url to the activity
        return reverse("committees:meetings:home", kwargs={"group_id": self.association_group.id})

    def __call__(self, *args, **kwargs):
        self.association_group = get_object_or_404(AssociationGroup, id=kwargs["group_id"])
        return super(MeetingCalendarFeed, self).__call__(*args, **kwargs)

    def items(self):
        activity = get_meeting_activity(self.association_group)
        unique_meetings = ActivityMoment.meetings.filter_group(self.association_group).exclude(
            status=ActivityStatus.STATUS_REMOVED
        )
        return [activity, *unique_meetings]
