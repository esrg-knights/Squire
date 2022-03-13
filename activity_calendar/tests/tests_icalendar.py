import icalendar
from datetime import timedelta, datetime

from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone, dateparse

from activity_calendar.models import Activity, ActivityMoment
from activity_calendar.feeds import CESTEventFeed, get_feed_id




class TestCaseICalendarExport(TestCase):
    fixtures = ['test_activity_recurrence_dst.json']

    # Ensure that only published activities are exported
    def test_only_published(self):
        non_published = Activity.objects.filter(title='Weekly activity').first()
        non_published.published_date = timezone.now() + timedelta(days=200)
        non_published.save()

        request = RequestFactory().get("/api/calendar/ical")
        view = CESTEventFeed()

        response = view(request)
        calendar = icalendar.Calendar.from_ical(response.content)

        vevents = [sub for sub in calendar.subcomponents if isinstance(sub, icalendar.cal.Event)]

        self.assertEquals(len(vevents), 1)
        self.assertEquals(vevents[0]["SUMMARY"].to_ical(), b"Weekly CEST Event")


    # Ensure that DST does not affect EXDATE's start dates
    def test_recurrence_dst(self):
        class DSTTestItemsFeed(CESTEventFeed):
            def items(self):
                return Activity.objects.filter(title='Weekly CEST Event')

        request = RequestFactory().get("/api/calendar/ical")
        view = DSTTestItemsFeed()

        response = view(request)
        calendar = icalendar.Calendar.from_ical(response.content)

        vevents = [sub for sub in calendar.subcomponents if isinstance(sub, icalendar.cal.Event)]

        self.assertEquals(len(vevents), 1)
        vevent = vevents[0]

        # Start and end date converted to local time
        self.assertEquals(vevent["DTSTART"].to_ical(), b"20200816T120000")
        self.assertEquals(vevent["DTSTART"].params["TZID"], "Europe/Amsterdam")

        self.assertEquals(vevent["DTEND"].to_ical(), b"20200816T173000")
        self.assertEquals(vevent["DTEND"].params["TZID"], "Europe/Amsterdam")

        # EXDATEs converted to local time.
        # NB: Their start times must match the start time of the event, as dst
        #   is automatically accounted for by calendar software
        self.assertEquals(vevent["EXDATE"].to_ical(), b"20201017T120000,20201114T120000")
        self.assertEquals(vevent["EXDATE"].params["TZID"], "Europe/Amsterdam")

    # Ensure that the VTIMEZONE field is correctly set
    def test_vtimezone(self):
        request = RequestFactory().get("/api/calendar/ical")
        view = CESTEventFeed()

        response = view(request)
        calendar = icalendar.Calendar.from_ical(response.content)

        vtimezones = [sub for sub in calendar.subcomponents if isinstance(sub, icalendar.cal.Timezone)]

        self.assertEquals(len(vtimezones), 1)
        vtimezone = vtimezones[0]

        self.assertEquals(vtimezone["TZID"], "Europe/Amsterdam")
        self.assertEquals(vtimezone["X-LIC-LOCATION"], "Europe/Amsterdam")

        for sub in vtimezone.subcomponents:
            if isinstance(sub, icalendar.cal.TimezoneDaylight):
                self.assertEqual(sub.name, "DAYLIGHT")
                self.assertEqual(sub["DTSTART"].to_ical(), b"20210328T020000")
                self.assertEqual(sub["TZNAME"].to_ical(), b"CEST")
                self.assertEqual(sub["TZOFFSETFROM"].to_ical(), "+0100")
                self.assertEqual(sub["TZOFFSETTO"].to_ical(), "+0200")
            elif isinstance(sub, icalendar.cal.TimezoneStandard):
                self.assertEqual(sub.name, "STANDARD")
                self.assertEqual(sub["DTSTART"].to_ical(), b"20201025T030000")
                self.assertEqual(sub["TZNAME"].to_ical(), b"CET")
                self.assertEqual(sub["TZOFFSETFROM"].to_ical(), "+0200")
                self.assertEqual(sub["TZOFFSETTO"].to_ical(), "+0100")
            else:
                self.fail(f"Only STANDARD or DAYLIGHT components must appear in VTIMEZONE. Got <{str(type(sub))}> instead!")


class ICalFeedTestCase(TestCase):
    fixtures = ['test_users', 'test_activity_slots']

    def setUp(self):
        self.feed = CESTEventFeed()
        self._build_response_calendar()

    def _build_response_calendar(self):
        request = RequestFactory().get("/api/calendar/ical")
        response = self.feed(request)
        self.calendar = icalendar.Calendar.from_ical(response.content)

    def _get_component(self, activity_item):
        """
        The calendar stream contains a collection of several components. This method returns the first
        component adhering to the given activity_id and (if given) recurrence_id
        :param activity_item: The activity or activitymoment instance
        :param recurrence_id: The recurrence id. Returns the first valid component if None.
        :return: The subcomponent from the calendar with the given data.
        """
        guid = get_feed_id(activity_item)

        for subcomponent in self.calendar.subcomponents:
            if subcomponent.get('UID', None) == guid and subcomponent.get('DTSTART').dt == activity_item.start_date:
                return subcomponent
        return None

    def test_activity_in_feed(self):
        activity = Activity.objects.get(id=2)
        component = self._get_component(activity)
        self.assertIsNotNone(component)
        self.assertIn('SUMMARY', component.keys())
        self.assertIn('DTSTART', component.keys())
        self.assertIn('DTEND', component.keys())
        self.assertIn('DESCRIPTION', component.keys())
        self.assertIn('LOCATION', component.keys())
        # Recurrence info
        self.assertIn('RRULE', component.keys())
        self.assertIn('EXDATE', component.keys())

        self.assertIn('URL', component.keys())
        self.assertEqual('/'+component['URL'].split('/', 3)[3], '/activities/')

    def test_extra_nonrecurrent_activitymoment(self):
        """ Tests that an activity outside the recurrence is in the feed """
        activitymoment = ActivityMoment.objects.get(id=5)
        component = self._get_component(activitymoment)
        self.assertIsNotNone(component, "There was no component for the extra activity instance")
        self.assertNotIn('RECURRENCE-ID', component.keys())

        self.assertIn('SUMMARY', component.keys())
        self.assertIn('DTSTART', component.keys())
        self.assertIn('DTEND', component.keys())
        self.assertIn('DESCRIPTION', component.keys())
        self.assertIn('LOCATION', component.keys())
        self.assertIn('URL', component.keys())
        self.assertEqual('/'+component['URL'].split('/', 3)[3], activitymoment.get_absolute_url())

    def test_overwritten_activitymoment(self):
        """ Tests that an activitymoment overwriting a recurrence moment is in the feed """
        activitymoment = ActivityMoment.objects.get(id=4)
        component = self._get_component(activitymoment)
        self.assertIsNotNone(component, "There was no component for the activity instance on the recurrence")
        self.assertIn('SUMMARY', component.keys())
        self.assertIn('DESCRIPTION', component.keys())
        self.assertIn('DTSTART', component.keys())
        self.assertIn('DTEND', component.keys())
        self.assertIn('LOCATION', component.keys())
        self.assertIn('URL', component.keys())

        self.assertEqual('/'+component['URL'].split('/', 3)[3], activitymoment.get_absolute_url())
        self.assertEqual(component.get('SUMMARY'), activitymoment.title)
        self.assertIn('RECURRENCE-ID', component.keys())
        self.assertEqual(component.get('RECURRENCE-ID').dt, activitymoment.recurrence_id)

    def test_non_recurrent_doubleglicth(self):
        """ Non-recurrent activities should have activity displayed ONLY when activitymoment is not present yet.
        Otherswise the activitymoment will appear next to instead of override activity.
        As described in issue #213 """

        activity = Activity.objects.get(id=1)
        component = self._get_component(activity)
        self.assertIsNone(component)

        # Clear activitymoments
        ActivityMoment.objects.filter(parent_activity_id=1).delete()
        # Refresh calendar response
        self._build_response_calendar()

        # Activity should no longer be None
        component = self._get_component(activity)
        self.assertIsNotNone(component)

    def test_moved_activitymoment_of_recurrent(self):
        """ Tests that an activitymoment that is moving a recurrent activity instance """
        activitymoment = ActivityMoment.objects.get(id=6)
        component = self._get_component(activitymoment)
        self.assertIsNotNone(component, "There was no component for the activity instance on the recurrence")
        self.assertIn('SUMMARY', component.keys())
        self.assertIn('DESCRIPTION', component.keys())
        self.assertIn('DTSTART', component.keys())
        self.assertIn('DTEND', component.keys())
        self.assertIn('LOCATION', component.keys())
        self.assertIn('URL', component.keys())

        self.assertEqual('/'+component['URL'].split('/', 3)[3], activitymoment.get_absolute_url())
        self.assertEqual(component.get('SUMMARY'), activitymoment.title)
        self.assertIn('RECURRENCE-ID', component.keys())
        self.assertEqual(component.get('RECURRENCE-ID').dt, activitymoment.recurrence_id)

    def test_cancelled_activitymoment(self):
        activitymoment = ActivityMoment.objects.get(id=6)
        component = self._get_component(activitymoment)
        self.assertIn('STATUS', component.keys())
        self.assertEqual(component['STATUS'], 'CONFIRMED')

        activitymoment.status = ActivityMoment.STATUS_CANCELLED
        activitymoment.save()
        self._build_response_calendar()
        component = self._get_component(activitymoment)

        self.assertIn('STATUS', component.keys())
        self.assertEqual(component['STATUS'], 'CANCELLED')

    def test_removed_activitymoment(self):
        activity = Activity.objects.get(id=2)
        activitymoment = ActivityMoment.objects.get(id=3)

        # An activity moment should show up and the EXDATE should only contain a given date from fixtures
        self.assertIsNotNone(self._get_component(activitymoment))
        self.assertTrue(any(filter(
            lambda exdate: exdate.dt == dateparse.parse_datetime('2020-10-21T14:00:00+00:00'),
            self._get_component(activity)['EXDATE'].dts)
        ))
        self.assertEqual(len(self._get_component(activity)['EXDATE'].dts), 2)

        # Cancel the activity
        activitymoment.status = ActivityMoment.STATUS_REMOVED
        activitymoment.save()
        self._build_response_calendar()

        # Check that it is now excluded from the calendar (not as a VVent and in the EXDATE)
        self.assertIsNone(self._get_component(activitymoment))
        self.assertTrue(any(filter(
            lambda exdate: exdate.dt == activitymoment.recurrence_id,
            self._get_component(activity)['EXDATE'].dts)
        ))
        self.assertEqual(len(self._get_component(activity)['EXDATE'].dts), 3)

