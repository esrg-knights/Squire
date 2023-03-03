from datetime import timedelta
from django.contrib.auth.models import Group
from django.test import TestCase

from committees.models import AssociationGroup

from activity_calendar.committee_pages.utils import get_meeting_activity, create_meeting_activity
from activity_calendar.constants import *
from activity_calendar.models import Activity


class ActivityCommmitteePageUtilsTestCase(TestCase):
    fixtures = ['activity_calendar/test_meetings']

    def test_get_meeting_activity(self):
        meeting_activity = get_meeting_activity(AssociationGroup.objects.get(id=40))
        self.assertEqual(meeting_activity.id, 40)
        self.assertIsInstance(meeting_activity, Activity)

    def test_create_meeting_activity(self):
        group = Group.objects.create(name='test_group')
        assoc_group = AssociationGroup.objects.create(site_group=group)

        meeting_activity = create_meeting_activity(assoc_group)
        self.assertEqual(meeting_activity.type, ACTIVITY_MEETING)
        self.assertEqual(meeting_activity.duration, timedelta(hours=1))
        self.assertTrue(meeting_activity.organisers.exists())
