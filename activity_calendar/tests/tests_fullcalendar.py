from datetime import timedelta
import json

from django.test import TestCase, Client
from django.utils import timezone

from activity_calendar.models import Activity
from activity_calendar.views import fullcalendar_feed
from core.util import suppress_warnings

class TestCaseFullCalendar(TestCase):
    fixtures = ['test_activity_recurrence_dst.json']

    def setUp(self):
        self.client = Client()

    def test_valid_dst_request(self):
        response = self.client.get('/api/calendar/fullcalendar', data={
            'start': "2020-10-14T00:00:00+02:00",
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

        for activity in activities:
            if activity.get('groupId') == 9:
                self.assertEqual(activity.get('title'), 'Weekly CEST Event')
                self.assertEqual(activity.get('start'), '2020-10-24T12:00:00+02:00')
                self.assertEqual(activity.get('end'), '2020-10-24T17:30:00+02:00')
            else:
                self.assertEqual(activity.get('groupId'), 1)
                self.assertEqual(activity.get('title'), 'Weekly activity')

                # Check pre- and post- DST-switch dates
                if not has_seen_pre_dst and activity.get('start') == '2020-10-20T19:30:00+02:00':
                    has_seen_pre_dst = True
                    self.assertEqual(activity.get('end'), '2020-10-21T04:00:00+02:00')
                elif not has_seen_post_dst and activity.get('start') == '2020-10-27T19:30:00+01:00':
                    has_seen_post_dst = True
                    self.assertEqual(activity.get('end'), '2020-10-28T04:00:00+01:00')
                else:
                    self.fail(f"Found a start-time that should not occur: <{activity.get('start')}>")

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
        self.assertEqual(activity.get('description'), 'Occurs every week, except once during daylight saving time (dst) and once during standard time!')
        self.assertEqual(activity.get('allDay'), False)
        self.assertEqual(activity.get('start'), '2020-10-24T12:00:00+02:00')
        self.assertEqual(activity.get('end'), '2020-10-24T17:30:00+02:00')

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
