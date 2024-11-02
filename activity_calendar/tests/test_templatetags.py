from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.test import TestCase
from django.utils import dateparse

from activity_calendar.constants import ActivityStatus
from activity_calendar.models import Activity, ActivityMoment
from activity_calendar.templatetags.activity_tags import readable_activity_datetime, get_next_activity_instances
from . import mock_now


class TestActivityTags(TestCase):
    fixtures = ["test_users.json", "test_activity_slots"]

    def setUp(self):
        self.activity_moment = ActivityMoment.objects.get(id=1)
        self.activity = self.activity_moment.parent_activity

    def _set_activity_vars(self, activity=None, **kwargs):
        """
        Set the activity variables on an activity
        :param activity: the activity, default: self.activity
        :param kwargs: any attribute of activity
        :return:
        """
        activity = activity or self.activity

        for key, value in kwargs.items():
            setattr(activity, key, value)
        activity.save()
        self.activity_moment.refresh_from_db()

    def test_readable_activity_datetime_normal(self):
        self._set_activity_vars(full_day=False, display_end_time=False)
        self.assertEqual(readable_activity_datetime(self.activity_moment), "Friday 14 August 21:00")

    def test_readable_activity_datetime_display_end_time(self):
        self._set_activity_vars(full_day=False, display_end_time=True)
        self.assertEqual(readable_activity_datetime(self.activity_moment), "Friday 14 August 21:00 - 23:00")

    def test_readable_activity_datetime_display_end_time_mulitple_days(self):
        self._set_activity_vars(
            full_day=False,
            display_end_time=True,
            end_date=datetime(2020, 8, 16, 10, 0, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(
            readable_activity_datetime(self.activity_moment), "Friday 14 August 21:00 - Sunday 16 August 12:00"
        )

    def test_readable_activity_datetime_full_day(self):
        self._set_activity_vars(full_day=True, display_end_time=False)
        self.assertEqual(readable_activity_datetime(self.activity_moment), "Friday 14 August")

    def test_readable_activity_datetime_full_day_display_end_time(self):
        self._set_activity_vars(full_day=True, display_end_time=True)
        self.assertEqual(readable_activity_datetime(self.activity_moment), "Friday 14 August")

    def test_readable_activity_datetime_full_day_display_end_time_over_multiple_days(self):
        self._set_activity_vars(
            full_day=True,
            display_end_time=True,
            end_date=datetime(2020, 8, 16, 10, 0, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(readable_activity_datetime(self.activity_moment), "Friday 14 August - Sunday 16 August")


class GetNextActivityInstancesTestCase(TestCase):
    fixtures = ["test_users.json", "test_activity_slots"]

    def setUp(self):
        self.activity = Activity.objects.get(id=2)

    @patch("django.utils.timezone.now", side_effect=mock_now())
    def test_default_start_dt(self, mock):
        instances = get_next_activity_instances(self.activity)
        self.assertEqual(instances[0].recurrence_id, dateparse.parse_datetime("2020-08-12T14:00:00+00:00"))

    def test_start_dt(self):
        instances = get_next_activity_instances(
            self.activity, start_dt=dateparse.parse_datetime("2020-08-19T00:00:00+00:00")
        )
        self.assertEqual(instances[0].recurrence_id, dateparse.parse_datetime("2020-08-19T14:00:00+00:00"))

    def test_override_recurrent_from_db(self):
        instances = get_next_activity_instances(
            self.activity, start_dt=dateparse.parse_datetime("2020-08-04T00:00:00+00:00")
        )
        self.assertEqual(instances[0].id, 2)
        self.assertEqual(instances[1].id, 3)
        self.assertEqual(instances[2].id, None)

    def test_max_items(self):
        instances = get_next_activity_instances(self.activity)
        self.assertEqual(len(instances), 3)
        instances = get_next_activity_instances(self.activity, max=5)
        self.assertEqual(len(instances), 5)

    def test_sequential_ordering(self):
        """Method should return a sequence from first to later in time"""
        instances = get_next_activity_instances(self.activity)
        for i in range(len(instances) - 1):
            self.assertLess(
                instances[i].recurrence_id,
                instances[i + 1].recurrence_id,
            )

    def test_activity_filter(self):
        instances = get_next_activity_instances(self.activity)
        self.assertEqual(instances[0].parent_activity, self.activity)

    def test_exclude_removed_events(self):
        removed_moment = self.activity.activitymoment_set.filter(status=ActivityStatus.STATUS_REMOVED).first()
        start_dt = removed_moment.recurrence_id - timedelta(hours=2)

        instances = get_next_activity_instances(self.activity, start_dt=start_dt)
        self.assertEqual(instances[0].recurrence_id, removed_moment.recurrence_id + timedelta(days=7))

    def test_limited_selection(self):
        start_dt = dateparse.parse_datetime("2020-08-12T19:00:00Z")
        instances = get_next_activity_instances(Activity.objects.get(id=1), start_dt=start_dt)
        self.assertEqual(len(instances), 1)
