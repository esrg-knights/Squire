from datetime import datetime, timedelta
import json

from django.test import TestCase, Client
from django.utils import timezone

from activity_calendar.models import Activity
from core.tests.util import suppress_warnings


def compare_iso_datetimes(dt_1, dt_2):
    return datetime.fromisoformat(dt_1) == datetime.fromisoformat(dt_2)

class TestCaseFullCalendar(TestCase):
    fixtures = ['test_activity_recurrence_dst.json']

    def setUp(self):
        self.client = Client()

    @classmethod
    def assertEqualDateTime(cls, original, compare_to):
        if not compare_iso_datetimes(original, compare_to):
            raise AssertionError(f'{compare_to} does not express the same time as {original}')


    def test_valid_dst_request(self):
        response = self.client.get('/api/calendar/fullcalendar', data={
            'start': "2020-10-14T08:00:00+02:00",
            'end': "2020-10-28T00:00:00+01:00",
        })

        # Ensure that the request is correctly handled
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')

        content = json.loads(response.content)
        activities = content.get('activities')

        # Ensure that the DST-switch is taken into account for the activity's start time
        has_seen_pre_dst = False
        has_seen_post_dst = False

        # There are three entries in this query.
        # 2 are of the same acticity in different time summer/wintertime schedules and should thus be shifted by an hour
        # There is also one other activity on an arbitrary moment

        for activity in activities:
            if activity.get('groupId') == 9:
                self.assertEqual(activity.get('title'), 'Weekly CEST Event')
                self.assertEqualDateTime(activity.get('start'), '2020-10-24T10:00:00+00:00')
                self.assertEqualDateTime(activity.get('end'), '2020-10-24T15:30:00+00:00')

            if activity.get('groupId') == 1:
                # There are two instances in this list for this activity
                if compare_iso_datetimes(activity.get('start'), '2020-10-20T19:30:00+02:00'):
                    self.assertEqualDateTime(activity.get('end'), '2020-10-21T04:00:00+02:00')
                    # It is in summer time
                    has_seen_pre_dst = True
                elif compare_iso_datetimes(activity.get('start'), '2020-10-27T19:30:00+01:00'):
                    self.assertEqualDateTime(activity.get('end'), '2020-10-28T04:00:00+01:00')
                    # It is in winter time
                    has_seen_post_dst = True
                else:
                    self.fail(f"Found an unexpected instance for this activity at: <{activity.get('start')}>")

        if not has_seen_pre_dst or not has_seen_post_dst:
            self.fail(f"The shift check was not valid. Either a pre or post timeshift instance was not found")

    def test_only_published(self):
        non_published = Activity.objects.filter(title='Weekly activity').first()
        non_published.published_date = timezone.now() + timedelta(days=200)
        non_published.save()

        response = self.client.get('/api/calendar/fullcalendar', data={
            'start': "2020-10-14T00:00:00+02:00",
            'end': "2020-10-28T00:00:00+01:00",
        })

        # Ensure that the request is correctly handled
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')

        content = json.loads(response.content)
        activities = content.get('activities')

        self.assertEqual(len(activities), 1)
        activity = activities[0]

        # Only published activities should be shown
        self.assertEqual(activity.get('groupId'), 9)
        self.assertEqual(activity.get('title'), 'Weekly CEST Event')
        self.assertEqual(activity.get('location'), 'Online')
        self.assertEqual(activity.get('description'), '<p>Occurs every week, except once during daylight saving time (dst) and once during standard time!</p>')
        self.assertEqual(activity.get('allDay'), False)

        self.assertEqualDateTime(activity.get('start'), '2020-10-24T10:00:00+00:00')
        self.assertEqualDateTime(activity.get('end'), '2020-10-24T15:30:00+00:00')

    @suppress_warnings
    def test_missing_start_or_end(self):
        response = self.client.get('/api/calendar/fullcalendar', data={})

        # Cannot request events without providing a start and end date
        self.assertEqual(response.status_code, 400)

    @suppress_warnings
    def test_too_long_timeframe(self):
        response = self.client.get('/api/calendar/fullcalendar', data={
            'start': "1970-01-01T00:00:00+02:00",
            'end': "1970-03-01T00:00:00+02:00",
        })

        # Cannot request activities for a timeframe of >42 days
        self.assertEqual(response.status_code, 400)

    @suppress_warnings
    def test_invalid_start_or_end(self):
        response = self.client.get('/api/calendar/fullcalendar', data={
            'start': "THIS-IS-NOT-A-DATE-TIME-STRING!!!",
            'end': "1970-03-01T00:00:00+02:00",
        })

        # Needs valid dt-strings
        self.assertEqual(response.status_code, 400)
