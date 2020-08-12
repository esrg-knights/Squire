from datetime import timedelta

from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone

from activity_calendar.models import Activity
from activity_calendar.feeds import CESTEventFeed, ExtendedICal20Feed

import icalendar

from django_ical.feedgenerator import ICal20Feed
from django_ical.views import ICalFeed


class TestItemsFeed(CESTEventFeed):
    feed_type = ExtendedICal20Feed
    title = "Test Feed"
    description = "Test ICal Feed"

class TestCaseICalendarExport(TestCase):
    fixtures = ['test_activity_recurrence_dst.json']

    # Ensure that only published activities are exported
    def test_only_published(self):
        non_published = Activity.objects.filter(title='Weekly activity').first()
        non_published.published_date = timezone.now() + timedelta(days=200)
        non_published.save()

        request = RequestFactory().get("/api/calendar/ical")
        view = TestItemsFeed()

        response = view(request)
        calendar = icalendar.Calendar.from_ical(response.content)

        vevents = [sub for sub in calendar.subcomponents if isinstance(sub, icalendar.cal.Event)]

        self.assertEquals(len(vevents), 1)
        self.assertEquals(vevents[0]["SUMMARY"].to_ical(), b"Weekly CEST Event")


    # Ensure that DST does not affect EXDATE's start dates
    def test_recurrence_dst(self):
        class DSTTestItemsFeed(TestItemsFeed):
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

        # EXDATEs converted to 'local' time.
        # NB: Their start times must match the start time of the event, regardless of
        # daylight saving time!
        self.assertEquals(vevent["EXDATE"].to_ical(), b"20201017T120000,20201114T120000")
        self.assertEquals(vevent["EXDATE"].params["TZID"], "Europe/Amsterdam")

    # Ensure that the VTIMEZONE field is correctly set
    def test_vtimezone(self):
        request = RequestFactory().get("/api/calendar/ical")
        view = TestItemsFeed()

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
                self.assertEqual(sub["DTSTART"].to_ical(), b"19700329T200000")
                self.assertEqual(sub["RRULE"].to_ical(), b"FREQ=YEARLY;BYDAY=-1SU;BYMONTH=3")
                self.assertEqual(sub["TZNAME"].to_ical(), b"CEST")
                self.assertEqual(sub["TZOFFSETFROM"].to_ical(), "+0100")
                self.assertEqual(sub["TZOFFSETTO"].to_ical(), "+0200")
            elif isinstance(sub, icalendar.cal.TimezoneStandard):
                self.assertEqual(sub.name, "STANDARD")
                self.assertEqual(sub["DTSTART"].to_ical(), b"19701025T030000")
                self.assertEqual(sub["RRULE"].to_ical(), b"FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10")
                self.assertEqual(sub["TZNAME"].to_ical(), b"CET")
                self.assertEqual(sub["TZOFFSETFROM"].to_ical(), "+0200")
                self.assertEqual(sub["TZOFFSETTO"].to_ical(), "+0100")
            else:
                self.fail(f"Only STANDARD or DAYLIGHT components must appear in VTIMEZONE. Got <{str(type(sub))}> instead!")
        