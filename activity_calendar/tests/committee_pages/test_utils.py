from datetime import timedelta
from django.contrib.auth.models import Group
from django.test import TestCase

from committees.models import AssociationGroup

from activity_calendar.committee_pages.utils import get_meeting_activity, create_meeting_activity
from activity_calendar.constants import ActivityType
from activity_calendar.models import Activity


class ActivityCommmitteePageUtilsTestCase(TestCase):
    fixtures = ["activity_calendar/test_meetings"]

    def test_get_meeting_activity(self):
        meeting_activity = get_meeting_activity(AssociationGroup.objects.get(id=60))
        self.assertEqual(meeting_activity.id, 60)
        self.assertIsInstance(meeting_activity, Activity)

    def test_create_meeting_activity(self):
        assoc_group = AssociationGroup.objects.create(name="test_group")

        meeting_activity = create_meeting_activity(assoc_group)
        self.assertEqual(meeting_activity.type, ActivityType.ACTIVITY_MEETING)
        self.assertEqual(meeting_activity.duration, timedelta(hours=1))
        self.assertTrue(meeting_activity.organisers.exists())
