import icalendar
from datetime import timedelta, datetime, date

from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone, dateparse

from membership_file.models import Member

from activity_calendar.constants import ActivityStatus
from activity_calendar.models import Activity, ActivityMoment, CalendarActivityLink
from activity_calendar.feeds import PublicCalendarFeed, get_feed_id, BirthdayCalendarFeed, CustomCalendarFeed


class TestCaseICalendarExport(TestCase):
    fixtures = ["test_activity_recurrence_dst.json"]

    # Ensure that only published activities are exported
    def test_only_published(self):
        non_published = Activity.objects.filter(title="Weekly activity").first()
        non_published.published_date = timezone.now() + timedelta(days=200)
        non_published.save()

        request = RequestFactory().get("/api/calendar/ical")
        view = PublicCalendarFeed()

        response = view(request)
        calendar = icalendar.Calendar.from_ical(response.content)

        vevents = [sub for sub in calendar.subcomponents if isinstance(sub, icalendar.cal.Event)]

        self.assertEqual(len(vevents), 1)
        self.assertEqual(vevents[0]["SUMMARY"].to_ical(), b"Weekly CEST Event")

    # Ensure that DST does not affect EXDATE's start dates
    def test_recurrence_dst(self):
        class DSTTestItemsFeed(PublicCalendarFeed):
            def items(self):
                return Activity.objects.filter(title="Weekly CEST Event")

        request = RequestFactory().get("/api/calendar/ical")
        view = DSTTestItemsFeed()

        response = view(request)
        calendar = icalendar.Calendar.from_ical(response.content)

        vevents = [sub for sub in calendar.subcomponents if isinstance(sub, icalendar.cal.Event)]

        self.assertEqual(len(vevents), 1)
        vevent = vevents[0]

        # Start and end date converted to local time
        self.assertEqual(vevent["DTSTART"].to_ical(), b"20200816T120000")
        self.assertEqual(vevent["DTSTART"].params["TZID"], "Europe/Amsterdam")

        self.assertEqual(vevent["DTEND"].to_ical(), b"20200816T173000")
        self.assertEqual(vevent["DTEND"].params["TZID"], "Europe/Amsterdam")

        # EXDATEs converted to local time.
        # NB: Their start times must match the start time of the event, as dst
        #   is automatically accounted for by calendar software
        self.assertEqual(vevent["EXDATE"].to_ical(), b"20201017T120000,20201114T120000")
        self.assertEqual(vevent["EXDATE"].params["TZID"], "Europe/Amsterdam")

    # Ensure that the VTIMEZONE field is correctly set
    def test_vtimezone(self):
        request = RequestFactory().get("/api/calendar/ical")
        view = PublicCalendarFeed()

        response = view(request)
        calendar = icalendar.Calendar.from_ical(response.content)

        vtimezones = [sub for sub in calendar.subcomponents if isinstance(sub, icalendar.cal.Timezone)]

        self.assertEqual(len(vtimezones), 1)
        vtimezone = vtimezones[0]

        self.assertEqual(vtimezone["TZID"], "Europe/Amsterdam")
        self.assertEqual(vtimezone["X-LIC-LOCATION"], "Europe/Amsterdam")

        self.assertEqual(len(vtimezone.subcomponents), 2)
        for sub in vtimezone.subcomponents:
            if isinstance(sub, icalendar.cal.TimezoneDaylight):
                self.assertEqual(sub.name, "DAYLIGHT")
                self.assertEqual(sub["DTSTART"].to_ical(), b"19700329T020000")
                self.assertEqual(sub["TZNAME"].to_ical(), b"CEST")
                self.assertEqual(sub["TZOFFSETFROM"].to_ical(), "+0100")
                self.assertEqual(sub["TZOFFSETTO"].to_ical(), "+0200")
                self.assertEqual(sub["RRULE"].to_ical(), b"FREQ=YEARLY;BYDAY=-1SU;BYMONTH=3")
            elif isinstance(sub, icalendar.cal.TimezoneStandard):
                self.assertEqual(sub.name, "STANDARD")
                self.assertEqual(sub["DTSTART"].to_ical(), b"19701025T030000")
                self.assertEqual(sub["TZNAME"].to_ical(), b"CET")
                self.assertEqual(sub["TZOFFSETFROM"].to_ical(), "+0200")
                self.assertEqual(sub["TZOFFSETTO"].to_ical(), "+0100")
                self.assertEqual(sub["RRULE"].to_ical(), b"FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10")
            else:
                self.fail(
                    f"Only STANDARD or DAYLIGHT components must appear in VTIMEZONE. Got <{str(type(sub))}> instead!"
                )


class FeedTestMixin:
    feed_class = None
    url_kwargs = {}

    def setUp(self):
        if self.feed_class is None:
            raise KeyError(f"Please define a feed_class in {self.__class__.__name__}")
        self.feed = self.feed_class()
        self._build_response_calendar(**self.url_kwargs)

    def _build_response_calendar(self, **url_kwargs):
        request = RequestFactory().get("/api/calendar/ical", data=url_kwargs)
        response = self.feed(request, **url_kwargs)
        self.calendar = icalendar.Calendar.from_ical(response.content)

    def _get_component(self, activity_item):
        """
        The calendar stream contains a collection of several components. This method returns the first
        component adhering to the given activity_id and (if given) recurrence_id
        :param activity_item: The activity or activitymoment instance
        :param recurrence_id: The recurrence id. Returns the first valid component if None.
        :return: The subcomponent from the calendar with the given data.
        """
        guid = self.feed.item_guid(activity_item)

        for subcomponent in self.calendar.subcomponents:
            start_dt = activity_item.start_date.date() if activity_item.full_day else activity_item.start_date

            if subcomponent.get("UID", None) == guid and subcomponent.get("DTSTART").dt == start_dt:
                return subcomponent
        return None


class ICalFeedTestCase(FeedTestMixin, TestCase):
    fixtures = ["test_users", "test_activity_slots"]
    feed_class = PublicCalendarFeed

    def test_activity_in_feed(self):
        activity = Activity.objects.get(id=2)
        component = self._get_component(activity)
        self.assertIsNotNone(component)
        self.assertIn("SUMMARY", component.keys())
        self.assertIn("DTSTART", component.keys())
        self.assertIn("DTEND", component.keys())
        self.assertIn("DESCRIPTION", component.keys())
        self.assertIn("LOCATION", component.keys())
        # Recurrence info
        self.assertIn("RRULE", component.keys())
        self.assertIn("EXDATE", component.keys())

        self.assertIn("URL", component.keys())
        self.assertEqual("/" + component["URL"].split("/", 3)[3], "/activities/")

    def test_guid(self):
        """Tests that instances of an activity share uid"""
        activitymoment = ActivityMoment.objects.get(id=4)
        self.assertEqual(activitymoment.is_part_of_recurrence, True)

        activity_component = self._get_component(activitymoment.parent_activity)
        activity_moment_component = self._get_component(activitymoment)
        self.assertEqual(str(activity_component["UID"]), str(activity_moment_component["UID"]))

        # Non-recurring activities should have a different uid
        activitymoment = ActivityMoment.objects.get(id=5)
        self.assertEqual(activitymoment.is_part_of_recurrence, False)

        activity_component = self._get_component(activitymoment.parent_activity)
        activity_moment_component = self._get_component(activitymoment)
        self.assertNotEqual(str(activity_component["UID"]), str(activity_moment_component["UID"]))

    def test_extra_nonrecurrent_activitymoment(self):
        """Tests that an activity outside the recurrence is in the feed"""
        activitymoment = ActivityMoment.objects.get(id=5)
        component = self._get_component(activitymoment)
        self.assertIsNotNone(component, "There was no component for the extra activity instance")
        self.assertNotIn("RECURRENCE-ID", component.keys())

        self.assertIn("SUMMARY", component.keys())
        self.assertIn("DTSTART", component.keys())
        self.assertIn("DTEND", component.keys())
        self.assertIn("DESCRIPTION", component.keys())
        self.assertIn("LOCATION", component.keys())
        self.assertIn("URL", component.keys())
        self.assertEqual("/" + component["URL"].split("/", 3)[3], activitymoment.get_absolute_url())

    def test_overwritten_activitymoment(self):
        """Tests that an activitymoment overwriting a recurrence moment is in the feed"""
        activitymoment = ActivityMoment.objects.get(id=4)
        component = self._get_component(activitymoment)
        self.assertIsNotNone(component, "There was no component for the activity instance on the recurrence")
        self.assertIn("SUMMARY", component.keys())
        self.assertIn("DESCRIPTION", component.keys())
        self.assertIn("DTSTART", component.keys())
        self.assertIn("DTEND", component.keys())
        self.assertIn("LOCATION", component.keys())
        self.assertIn("URL", component.keys())

        self.assertEqual("/" + component["URL"].split("/", 3)[3], activitymoment.get_absolute_url())
        self.assertEqual(component.get("SUMMARY"), activitymoment.title)
        self.assertIn("RECURRENCE-ID", component.keys())
        self.assertEqual(component.get("RECURRENCE-ID").dt, activitymoment.recurrence_id)

    def test_non_recurrent_doubleglitch(self):
        """Non-recurrent activities should have activity displayed ONLY when activitymoment is not present yet.
        Otherswise the activitymoment will appear next to instead of override activity.
        As described in issue #213"""

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
        """Tests that an activitymoment that is moving a recurrent activity instance"""
        activitymoment = ActivityMoment.objects.get(id=6)
        component = self._get_component(activitymoment)
        self.assertIsNotNone(component, "There was no component for the activity instance on the recurrence")
        self.assertIn("SUMMARY", component.keys())
        self.assertIn("DESCRIPTION", component.keys())
        self.assertIn("DTSTART", component.keys())
        self.assertIn("DTEND", component.keys())
        self.assertIn("LOCATION", component.keys())
        self.assertIn("URL", component.keys())

        self.assertEqual("/" + component["URL"].split("/", 3)[3], activitymoment.get_absolute_url())
        self.assertEqual(component.get("SUMMARY"), activitymoment.title)
        self.assertIn("RECURRENCE-ID", component.keys())
        self.assertEqual(component.get("RECURRENCE-ID").dt, activitymoment.recurrence_id)

    def test_cancelled_activitymoment(self):
        activitymoment = ActivityMoment.objects.get(id=6)
        component = self._get_component(activitymoment)
        self.assertIn("STATUS", component.keys())
        self.assertEqual(component["STATUS"], "CONFIRMED")

        activitymoment.status = ActivityStatus.STATUS_CANCELLED
        activitymoment.save()
        self._build_response_calendar()
        component = self._get_component(activitymoment)

        self.assertIn("STATUS", component.keys())
        self.assertEqual(component["STATUS"], "CANCELLED")

    def test_removed_activitymoment(self):
        activity = Activity.objects.get(id=2)
        activitymoment = ActivityMoment.objects.get(id=3)

        # An activity moment should show up and the EXDATE should only contain a given date from fixtures
        # NB: Datetime in the EXDATE from the fixture is localized to Europe/Amsterdam
        self.assertIsNotNone(self._get_component(activitymoment))
        self.assertTrue(
            any(
                filter(
                    lambda exdate: exdate.dt
                    == dateparse.parse_datetime("2020-10-21T16:00:00").replace(tzinfo=timezone.get_current_timezone()),
                    self._get_component(activity)["EXDATE"].dts,
                )
            )
        )
        self.assertEqual(len(self._get_component(activity)["EXDATE"].dts), 2)

        # Cancel the activity
        activitymoment.status = ActivityStatus.STATUS_REMOVED
        activitymoment.save()
        self._build_response_calendar()

        # Check that it is now excluded from the calendar (not as a VVent and in the EXDATE)
        self.assertIsNone(self._get_component(activitymoment))

        self.assertTrue(
            any(
                filter(
                    lambda exdate: exdate.dt.replace(tzinfo=timezone.get_current_timezone())
                    == activitymoment.recurrence_id,
                    self._get_component(activity)["EXDATE"].dts,
                )
            )
        )
        self.assertEqual(len(self._get_component(activity)["EXDATE"].dts), 3)

    def test_full_day_events(self):
        """Asserts that when a day is marked as full day, a date is given instead"""
        activity = Activity.objects.get(id=3)
        component = self._get_component(activity)
        self.assertIsNotNone(component)
        self.assertIsInstance(component["DTSTART"].dt, datetime)
        self.assertIsInstance(component["DTEND"].dt, datetime)

        # Make activity a full day activity
        activity.full_day = True
        activity.save()
        self._build_response_calendar()
        component = self._get_component(activity)
        self.assertIsNotNone(component)
        # start and end times should now be dates instead of datetimes
        self.assertIsInstance(component["DTSTART"].dt, date)
        self.assertIsInstance(component["DTEND"].dt, date)

        # test that the day is one day more than the original day
        # end day is not taken into account by calendar software as it is interpreted at day 0:00
        self.assertEqual(activity.end_date.date(), component["DTEND"].dt - timedelta(days=1))


class CustomCalendarFeedTestCase(FeedTestMixin, TestCase):
    fixtures = ["test_users", "test_activity_slots", "activity_calendar/test_custom_feed"]
    feed_class = CustomCalendarFeed
    url_kwargs = {"calendar_slug": "test_calendar"}

    def test_included_non_recurrent(self):
        """Test that a single activity with custom activitymoment settings does not present double"""
        # Assert link existence
        self.assertTrue(CalendarActivityLink.objects.filter(activity_id=1, calendar_id=1).exists())

        activity = Activity.objects.get(id=1)
        component = self._get_component(activity)
        self.assertIsNone(component)

        component = self._get_component(activity.activitymoment_set.first())
        self.assertIsNotNone(component)

    def test_included_recurrent(self):
        activity = Activity.objects.get(id=2)
        component = self._get_component(activity)
        self.assertIsNotNone(component)

        # Test that it also loads overwritten activitymoments
        component = self._get_component(activity.activitymoment_set.first())
        self.assertIsNotNone(component)

    def test_excluded(self):
        activity = Activity.objects.get(id=3)
        component = self._get_component(activity)
        self.assertIsNone(component)


class BirthdayFeedTestCase(FeedTestMixin, TestCase):
    fixtures = ["activity_calendar/test_birthdays"]
    feed_class = BirthdayCalendarFeed

    def test_generated_birthdays(self):
        """Tests that the birthdays that should be present are"""
        member = Member.objects.get(id=25)
        activity = BirthdayCalendarFeed.construct_birthday(member)
        component = self._get_component(activity)
        self.assertIsNotNone(component)
        self.assertEqual(component["DTSTART"].dt, member.date_of_birth)
        self.assertEqual(component["DTEND"].dt, member.date_of_birth)

        member = Member.objects.get(id=27)
        activity = BirthdayCalendarFeed.construct_birthday(member)
        component = self._get_component(activity)
        self.assertIsNotNone(component)
        self.assertEqual(component["DTSTART"].dt, member.date_of_birth)
        self.assertEqual(component["DTEND"].dt, member.date_of_birth)

    def test_exclude_nonshared_birthdays(self):
        """Members who do not want to share their birthday should be in here"""
        member = Member.objects.get(id=26)
        activity = BirthdayCalendarFeed.construct_birthday(member)
        component = self._get_component(activity)
        self.assertIsNone(component)

        # Make sure that the member is considered member so the testcase data is still correct
        self.assertTrue(member.is_active, msg="Data incorrect. Member 26 should be a current member")

    def test_exclude_nonmembers(self):
        member = Member.objects.get(id=26)
        activity = BirthdayCalendarFeed.construct_birthday(member)
        component = self._get_component(activity)
        self.assertIsNone(component)

        # Make sure that the old-member still wants to share their birthday
        self.assertFalse(
            member.membercalendarsettings.use_birthday,
            msg="Data incorrect. MemberCalendarSettings 28 should have use_birthday set to true",
        )
