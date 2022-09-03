from datetime import timezone as tz

from django.test import TestCase
from django.utils import timezone

from unittest.mock import patch

from . import mock_now

from activity_calendar.models import Activity, ActivityMoment
from activity_calendar.templatetags.activity_tags import readable_activity_datetime


class TestActivityTags(TestCase):
    fixtures = ['test_users.json', 'test_activity_slots']

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
        self._set_activity_vars(
            full_day = False,
            display_end_time = False
        )
        self.assertEqual(readable_activity_datetime(self.activity_moment), "Friday 14 August 21:00")

    def test_readable_activity_datetime_display_end_time(self):
        self._set_activity_vars(
            full_day = False,
            display_end_time = True
        )
        self.assertEqual(readable_activity_datetime(self.activity_moment), "Friday 14 August 21:00 - 23:00")


    def test_readable_activity_datetime_display_end_time_mulitple_days(self):
        self._set_activity_vars(
            full_day = False,
            display_end_time = True,
            end_date = timezone.datetime(2020, 8, 16, 10, 0, 0, tzinfo=timezone.utc)
        )

        self.assertEqual(readable_activity_datetime(self.activity_moment), "Friday 14 August 21:00 - Sunday 16 August 12:00")


    def test_readable_activity_datetime_full_day(self):
        self._set_activity_vars(
            full_day = True,
            display_end_time = False
        )
        self.assertEqual(readable_activity_datetime(self.activity_moment), "Friday 14 August")

    def test_readable_activity_datetime_full_day_display_end_time(self):
        self._set_activity_vars(
            full_day = True,
            display_end_time = True
        )
        self.assertEqual(readable_activity_datetime(self.activity_moment), "Friday 14 August")

    def test_readable_activity_datetime_full_day_display_end_time_over_multiple_days(self):
        self._set_activity_vars(
            full_day = True,
            display_end_time = True,
            end_date = timezone.datetime(2020, 8, 16, 10, 0, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(readable_activity_datetime(self.activity_moment), "Friday 14 August - Sunday 16 August")




