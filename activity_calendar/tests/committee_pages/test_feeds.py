from django.test import TestCase
from django.urls import reverse

from committees.models import AssociationGroup

from activity_calendar.constants import ActivityStatus
from activity_calendar.models import Activity, ActivityMoment
from activity_calendar.tests.tests_icalendar import FeedTestMixin
from activity_calendar.committee_pages.feeds import MeetingCalendarFeed


class MeetingCalendarFeedTestCase(FeedTestMixin, TestCase):
    fixtures = ["test_users", "test_activity_slots", "activity_calendar/test_meetings"]
    feed_class = MeetingCalendarFeed
    url_kwargs = {"group_id": 60}

    def test_general_properties(self):
        association_group = AssociationGroup.objects.get(id=self.url_kwargs["group_id"])
        self.assertEqual(self.feed.product_id, f"-//Squire//{association_group.name} Meeting Calendar//EN")
        self.assertEqual(self.feed.calendar_title, f"{association_group.name} meetings agenda - Knights")
        self.assertEqual(
            self.feed.calendar_description,
            f"Calendar for meetings for {association_group.name}. Provided by Squire, the Knights WebApp",
        )
        self.assertEqual(
            self.feed.item_link(None), reverse("committees:meetings:home", kwargs={"group_id": association_group.id})
        )

    def test_include_meeting(self):
        """Test that a single activity with custom activitymoment settings does not present double"""
        # Assert link existence
        # self.assertTrue(CalendarActivityLink.objects.filter(activity_id=1, calendar_id=1).exists())

        activity = Activity.objects.get(id=60)
        component = self._get_component(activity)
        self.assertIsNotNone(component)

        component = self._get_component(activity.activitymoment_set.first())
        self.assertIsNotNone(component)

    def test_exclude_meeting_from_other_groups(self):
        activity = Activity.objects.get(id=65)
        component = self._get_component(activity)
        self.assertIsNone(component)

        component = self._get_component(activity.activitymoment_set.first())
        self.assertIsNone(component)

    def test_cancelled_meetings(self):
        """Tests that a meeting includes cancelled moments"""
        activitymoment = ActivityMoment.objects.get(id=62)
        activitymoment.status = ActivityStatus.STATUS_REMOVED
        component = self._get_component(activitymoment)
        self.assertIsNotNone(component)
