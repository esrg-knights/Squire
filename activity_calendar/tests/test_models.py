from datetime import datetime

from django.contrib.auth.models import AnonymousUser
from django.core.validators import ValidationError
from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from unittest.mock import patch
from recurrence import deserialize as deserialize_recurrence_test

from . import mock_now

from activity_calendar.models import Activity, ActivitySlot, Participant, ActivityMoment
from core.models import ExtendedUser as User


# Tests model properties related to fetching participants, slots, etc.
class ModelMethodsTest(TestCase):
    fixtures = ['test_users.json', 'test_activity_methods']

    def setUp(self):
        self.activity = Activity.objects.get(id=2)

    # Should provide the correct url if the activity has an image, or the default image if no image is given
    def test_image_url(self):
        self.assertEqual(self.activity.image_url, f"{settings.MEDIA_URL}images/presets/rpg.jpg")

        self.activity.slots_image = None
        self.assertEqual(self.activity.image_url, f"{settings.STATIC_URL}images/default_logo.png")


class ModelMethodsDSTDependentTests(TestCase):
    """
        Tests model methods that change behaviour based on Daylight Saving Time
    """

    def setUp(self):
        activity_data = {
            'id': 4,
            'title': 'DST Test Event',
            # Start/end dates are during CET (UTC+1)
            # Start dt: 01 JAN 2020, 15.00 (CET)
            'start_date': timezone.datetime(2020, 1, 1, 14, 0, 0, tzinfo=timezone.utc),
            'end_date': timezone.datetime(2020, 1, 1, 18, 0, 0, tzinfo=timezone.utc),
            'recurrences': "RRULE:FREQ=WEEKLY;BYDAY=TU"
        }
        self.activity = Activity(**activity_data)

    @patch('django.utils.timezone.now', side_effect=mock_now(timezone.datetime(2020, 3, 20, 0, 0)))
    def test_has_occurence_at_same_dst(self, mock_tz):
        """
            Query an activity ocurrence when
            - that activity's first occurence was in CET
            - our current timezone is in CET
            - the queried occurence is in CET
        """
        query_dt = timezone.make_aware(timezone.datetime(2020, 10, 27, 15, 0, 0), timezone.pytz.timezone("Europe/Amsterdam"))

        has_occurence_at_query_dt = self.activity.has_occurrence_at(query_dt)
        self.assertTrue(has_occurence_at_query_dt)

    @patch('django.utils.timezone.now', side_effect=mock_now(timezone.datetime(2020, 3, 20, 0, 0)))
    def test_CET_has_occurence_at_CET_to_CEST(self, mock_tz):
        """
            Query an activity ocurrence when
            - that activity's first occurence was in CET
            - our current timezone is in CET
            - the queried occurence is in CEST
        """
        query_dt = timezone.make_aware(timezone.datetime(2020, 3, 31, 15, 0, 0), timezone.pytz.timezone("Europe/Amsterdam"))

        has_occurence_at_query_dt = self.activity.has_occurrence_at(query_dt)
        self.assertTrue(has_occurence_at_query_dt)

    @patch('django.utils.timezone.now', side_effect=mock_now(timezone.datetime(2020, 3, 20, 0, 0)))
    def test_CET_has_occurence_at_CEST_to_CET(self, mock_tz):
        """
            Query an activity ocurrence when
            - that activity's first occurence was in CEST
            - our current timezone is in CET
            - the queried occurence is in CET
        """
        # Make start/end date in CEST (UTC+2)
        # Start dt: 01 MAR 2020, 16.00 (CEST)
        self.activity.start_date = timezone.datetime(2020, 6, 1, 14, 0, 0, tzinfo=timezone.utc)
        self.activity.end_date = timezone.datetime(2020, 6, 1, 18, 0, 0, tzinfo=timezone.utc)

        query_dt = timezone.make_aware(timezone.datetime(2020, 10, 27, 16, 0, 0), timezone.pytz.timezone("Europe/Amsterdam"))

        has_occurence_at_query_dt = self.activity.has_occurrence_at(query_dt)
        self.assertTrue(has_occurence_at_query_dt)

    @patch('django.utils.timezone.now', side_effect=mock_now(timezone.datetime(2020, 10, 20, 0, 0)))
    def test_CEST_has_occurence_at_CET_to_CEST(self, mock_tz):
        """
            Query an activity ocurrence when
            - that activity's first occurence was in CET
            - our current timezone is in CEST
            - the queried occurence is in CEST
        """
        query_dt = timezone.make_aware(timezone.datetime(2020, 3, 31, 15, 0, 0), timezone.pytz.timezone("Europe/Amsterdam"))

        has_occurence_at_query_dt = self.activity.has_occurrence_at(query_dt)
        self.assertTrue(has_occurence_at_query_dt)

    @patch('django.utils.timezone.now', side_effect=mock_now(timezone.datetime(2020, 10, 20, 0, 0)))
    def test_CEST_has_occurence_at_CEST_to_CET(self, mock_tz):
        """
            Query an activity ocurrence when
            - that activity's first occurence was in CEST
            - our current timezone is in CET
            - the queried occurence is in CET
        """
        # Make start/end date in CEST (UTC+2)
        # Start dt: 01 MAR 2020, 16.00 (CEST)
        self.activity.start_date = timezone.datetime(2020, 6, 1, 14, 0, 0, tzinfo=timezone.utc)
        self.activity.end_date = timezone.datetime(2020, 6, 1, 18, 0, 0, tzinfo=timezone.utc)

        query_dt = timezone.make_aware(timezone.datetime(2020, 10, 27, 16, 0, 0), timezone.pytz.timezone("Europe/Amsterdam"))

        has_occurence_at_query_dt = self.activity.has_occurrence_at(query_dt)
        self.assertTrue(has_occurence_at_query_dt)


class EXDATEandRDATEwithDSTTests(TestCase):
    """
        Tests RDATEs and EXDATEs in combination with Daylight Saving Time
    """

    def setUp(self):
        self.recurrence_iso = "RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=TU"

        activity_data = {
            'id': 4,
            'title': 'DST Test Event 2: Electric Boogaloo',
            # Start/end dates are during CET (UTC+1)
            # Start dt: 03 NOV 2020, 19.00 (CET)
            'start_date': timezone.datetime(2020, 11, 3, 18, 0, 0, tzinfo=timezone.utc),
            'end_date': timezone.datetime(2020, 11, 3, 23, 30, 0, tzinfo=timezone.utc),
            'recurrences': self.recurrence_iso
        }
        self.activity = Activity(**activity_data)

    @patch('django.utils.timezone.now', side_effect=mock_now(timezone.datetime(2020, 12, 3, 0, 0)))
    def test_RDATE_EXDATE_at_same_dst(self, mock_tz):
        """
            Query RDATEs and EXDATEs when:
            - the activity's first occurence was in CET
            - our current timezone is in CET
            - RDATE/EXDATE are in CET

            RDATEs: Wednesday 30 December 2020
            EXDATEs: Tuesday 29 December 2020, Tuesday 12 January 2020
        """
        self.recurrence_iso += "\n\nRDATE:20201229T230000Z"
        self.recurrence_iso += "\nEXDATE:20201228T230000Z\nEXDATE:20210111T230000Z"
        self.activity.recurrences = deserialize_recurrence_test(self.recurrence_iso)

        # 30 December RDATE
        rdate_dt = timezone.make_aware(timezone.datetime(2020, 12, 30, 19, 0, 0), timezone.pytz.timezone("Europe/Amsterdam"))
        self.assertTrue(self.activity.has_occurrence_at(rdate_dt))

        # 29 December EXDATE
        exdate_dt = timezone.make_aware(timezone.datetime(2020, 12, 29, 19, 0, 0), timezone.pytz.timezone("Europe/Amsterdam"))
        self.assertFalse(self.activity.has_occurrence_at(exdate_dt))

        # 12 January EXDATE
        exdate_dt = timezone.make_aware(timezone.datetime(2021, 1, 12, 19, 0, 0), timezone.pytz.timezone("Europe/Amsterdam"))
        self.assertFalse(self.activity.has_occurrence_at(exdate_dt))

    @patch('django.utils.timezone.now', side_effect=mock_now(timezone.datetime(2020, 12, 3, 0, 0)))
    def test_CET_RDATE_EXDATE_CET_to_CEST(self, mock_tz):
        """
            Query RDATEs and EXDATEs when:
            - the activity's first occurence was in CET
            - our current timezone is in CET
            - RDATE/EXDATE are in CEST
        """
        self._test_RDATE_EXDATE_CET_to_CEST()

    @patch('django.utils.timezone.now', side_effect=mock_now(timezone.datetime(2021, 5, 1, 0, 0)))
    def test_CEST_RDATE_EXDATE_CET_to_CEST(self, mock_tz):
        """
            Query RDATEs and EXDATEs when:
            - the activity's first occurence was in CET
            - our current timezone is in CEST
            - RDATE/EXDATE are in CEST
        """
        self._test_RDATE_EXDATE_CET_to_CEST()

    def _test_RDATE_EXDATE_CET_to_CEST(self):
        """
            Query RDATEs and EXDATEs when:
            - the activity's first occurence was in CET
            - RDATE/EXDATE are in CEST

            The current timezone is set in a calling function

            RDATEs: Monday 17 April 2021
            EXDATE: Tuesday 4 April 2021
        """
        self.recurrence_iso += "\n\nRDATE:20210416T220000Z"
        self.recurrence_iso += "\nEXDATE:20210403T220000Z"
        self.activity.recurrences = deserialize_recurrence_test(self.recurrence_iso)

        # 17 April RDATE
        rdate_dt = timezone.make_aware(timezone.datetime(2021, 4, 17, 19, 0, 0), timezone.pytz.timezone("Europe/Amsterdam"))
        self.assertTrue(self.activity.has_occurrence_at(rdate_dt))

        # 04 April EXDATE
        exdate_dt = timezone.make_aware(timezone.datetime(2021, 4, 4, 19, 0, 0), timezone.pytz.timezone("Europe/Amsterdam"))
        self.assertFalse(self.activity.has_occurrence_at(exdate_dt))

    @patch('django.utils.timezone.now', side_effect=mock_now(timezone.datetime(2020, 12, 3, 0, 0)))
    def test_CET_RDATE_EXDATE_CEST_to_CET(self, mock_tz):
        """
            Query RDATEs and EXDATEs when:
            - the activity's first occurence was in CEST
            - our current timezone is in CET
            - RDATE/EXDATE are in CET
        """
        self._test_RDATE_EXDATE_CEST_to_CET()

    @patch('django.utils.timezone.now', side_effect=mock_now(timezone.datetime(2021, 5, 1, 0, 0)))
    def test_CEST_RDATE_EXDATE_CEST_to_CET(self, mock_tz):
        """
            Query RDATEs and EXDATEs when:
            - the activity's first occurence was in CEST
            - our current timezone is in CET
            - RDATE/EXDATE are in CET
        """
        self._test_RDATE_EXDATE_CEST_to_CET()

    def _test_RDATE_EXDATE_CEST_to_CET(self):
        """
            Query RDATEs and EXDATEs when:
            - the activity's first occurence was in CEST
            - RDATE/EXDATE are in CET

            The current timezone is set in a calling function

            RDATEs: Thursday 22 October 2020
            EXDATE: Tuesday 27 October 2020
        """
        # Start dt: 20 OCT 2020, 19.00 (CEST; UTC+2)
        self.activity.start_date = timezone.datetime(2020, 10, 20, 17, 0, 0, tzinfo=timezone.utc)

        self.recurrence_iso += "\n\nRDATE:20201021T230000Z"
        self.recurrence_iso += "\nEXDATE:20201026T230000Z"
        self.activity.recurrences = deserialize_recurrence_test(self.recurrence_iso)

        # 22 October RDATE
        rdate_dt = timezone.make_aware(timezone.datetime(2020, 10, 22, 19, 0, 0), timezone.pytz.timezone("Europe/Amsterdam"))
        self.assertTrue(self.activity.has_occurrence_at(rdate_dt))

        # 27 October EXDATE
        exdate_dt = timezone.make_aware(timezone.datetime(2020, 10, 27, 19, 0, 0), timezone.pytz.timezone("Europe/Amsterdam"))
        self.assertFalse(self.activity.has_occurrence_at(exdate_dt))


class TestCaseActivityClean(TestCase):
    fixtures = []

    def setUp(self):
        # Make an Activity
        self.base_activity_dict = {
            'title':        "Test Activity",
            'description':  "This is a testcase!\n\nWith a cool new line!",
            'location':     "In a testcase",
            'start_date':   timezone.get_current_timezone().localize(datetime(1970, 1, 1, 0, 0), is_dst=None),
            'end_date':     timezone.get_current_timezone().localize(datetime(1970, 1, 1, 23, 59), is_dst=None),
        }
        self.base_activity = Activity.objects.create(**self.base_activity_dict)

    def test_clean_valid(self):
        self.base_activity.title = "Updated!"
        self.base_activity.clean_fields()

    # Start date must be after end date
    def test_clean_wrong_start_date(self):
        self.base_activity.start_date = datetime(1971, 1, 1).astimezone(timezone.get_current_timezone())

        with self.assertRaises(ValidationError) as error:
            self.base_activity.clean_fields()

    # Must have a recurrence rule if excluding dates
    def test_clean_exdate_no_rdate(self):
        self.base_activity.recurrences = deserialize_recurrence_test("EXDATE:19700101T230000Z")

        with self.assertRaises(ValidationError) as error:
            self.base_activity.clean_fields()

    # EXRULEs are no longer supported
    def test_clean_deprecated_EXRULE(self):
        self.base_activity.recurrences = deserialize_recurrence_test("EXRULE:FREQ=WEEKLY;BYDAY=TU")

        with self.assertRaises(ValidationError) as error:
            self.base_activity.clean_fields()

    # Multiple RRULES are not supported
    def test_clean_multiple_RRULEs(self):
        self.base_activity.recurrences = deserialize_recurrence_test("RRULE:FREQ=WEEKLY;BYDAY=TU\nRRULE:FREQ=WEEKLY;BYDAY=MO")

        with self.assertRaises(ValidationError) as error:
            self.base_activity.clean_fields()

    # Must not throw validation errors if everything is defined correctly
    def test_clean_correct(self):
        self.base_activity.clean_fields()

        self.base_activity.recurrences = deserialize_recurrence_test("RDATE:19700101T230000Z")
        self.base_activity.clean_fields()


class ActivityTestCase(TestCase):
    fixtures = ['test_users.json', 'test_activity_slots']

    def setUp(self):
        self.activity = Activity.objects.get(id=2)

    def test_get_activitymoments_between(self):
        """ Tests the Activity get_activitymoments_between method"""
        after = timezone.datetime(2020, 10, 2, 0, 0, 0, tzinfo=timezone.utc)
        before = timezone.datetime(2020, 10, 16, 0, 0, 0, tzinfo=timezone.utc)
        activity_moments = self.activity.get_activitymoments_between(after, before)

        # There are two activities
        self.assertEqual(len(activity_moments), 2)
        dts = [
            timezone.datetime(2020, 10, 7, 14, 0, 0, tzinfo=timezone.utc),
            timezone.datetime(2020, 10, 14, 14, 0, 0, tzinfo=timezone.utc),
        ]
        # Check if all expected dates are present and not a single one more
        for activity_moment in activity_moments:
            for i in range(len(dts)):
                if activity_moment.recurrence_id == dts[i]:
                    del dts[i]
                    break
            else:
                raise AssertionError(f"ActivityMoment at {activity_moment.recurrence_id} was unexpected")
        for i in range(len(dts)):
            raise AssertionError(f'dts[i] was not found in the ActivityMoment instances')

        # Test that the data was indeed retrieved from the server
        for activity_moment in activity_moments:
            if activity_moment.id == 4:
                if activity_moment.local_title != "Different_boardgame_title":
                    raise AssertionError("ActivityMoment corresponding with rrule was not accurate from the database")
                else:
                    break
        else:
            raise AssertionError("ActivityMoments from rrule overwritten database instances or were not obtained")


    def test_get_occurrences_starting_between(self):
        """ Tests the get_occurrences_starting_between method, returning all activities according to the recurring rules """
        after = timezone.datetime(2020, 10, 2, 0, 0, 0, tzinfo=timezone.utc)
        before = timezone.datetime(2020, 10, 16, 0, 0, 0, tzinfo=timezone.utc)
        recurrences = list(self.activity.get_occurrences_starting_between(after, before))

        self.assertEqual(len(recurrences), 2)
        self.assertEqual(recurrences[0], timezone.datetime(2020, 10, 7, 14, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(recurrences[1], timezone.datetime(2020, 10, 14, 14, 0, 0, tzinfo=timezone.utc))

    def test_get_occurrences_starting_between_exclude(self):
        """ Tests the get_occurrences_starting_between method, confirms that excluded dates are processed accurately """
        after = timezone.datetime(2020, 10, 16, 0, 0, 0, tzinfo=timezone.utc)
        before = timezone.datetime(2020, 10, 23, 0, 0, 0, tzinfo=timezone.utc)
        recurrences = list(self.activity.get_occurrences_starting_between(after, before))

        # There is normally an activity on the 21st, but it's excluded so it doesn't happen.
        self.assertEqual(len(recurrences), 0)

    def test_get_occurrences_between_multi_day_activity(self):
        """ Tests if an occurrence starting before the specified time, but ending after it
            (thus still partially taking place during the specified period) is included """
        # Note: Activity has an occurrence on 07-10-21, which ends the next day at 02:00 (UTC)
        after = timezone.datetime(2020, 10, 8, 0, 0, 0, tzinfo=timezone.utc)
        before = timezone.datetime(2020, 10, 10, 0, 0, 0, tzinfo=timezone.utc)
        recurrences = list(self.activity.get_activitymoments_between(after, before))

        self.assertEqual(len(recurrences), 1)
        self.assertEqual(recurrences[0].recurrence_id, timezone.datetime(2020, 10, 7, 14, 0, 0, tzinfo=timezone.utc))

        # The activity does not START betwee the specified bounds
        self.assertEqual(len(list(self.activity.get_occurrences_starting_between(after, before))), 0)

    def _test_get_activitymoments_between(self, expected_occurrences, recurrence_id=None,
            new_start_date=None, new_end_date=None, after=None, before=None):
        """
            Tests if an activitymoment for an occurrence at a specified recurrence_id with
            specified alternative start and end times, is included/excluded in
            get_activitymoments_between
        """
        recurrence_id = recurrence_id or timezone.datetime(2020, 10, 14, 14, 0, 0, tzinfo=timezone.utc)
        self.activity_moment, _ = ActivityMoment.objects.get_or_create(
            parent_activity=self.activity,
            recurrence_id=recurrence_id,
        )

        # Set alternative start/end dates
        self.activity_moment.local_start_date = new_start_date
        self.activity_moment.local_end_date = new_end_date
        self.activity_moment.save()

        # Get activitymoments in this interval
        after = after or timezone.datetime(2020, 10, 9, 0, 0, 0, tzinfo=timezone.utc)
        before = before or timezone.datetime(2020, 10, 16, 0, 0, 0, tzinfo=timezone.utc)
        activity_moments = list(self.activity.get_activitymoments_between(after, before))

        # All expected occurrences should be there
        for occ in expected_occurrences:
            self.assertTrue(any(activity_moment.recurrence_id == occ for activity_moment in activity_moments),
                f"expected occurrence {occ} not in returned activitymoments {activity_moments}")

        # No unexpected acitivitymoments should be in there
        for am in activity_moments:
            self.assertTrue(any(am.recurrence_id == occ for occ in expected_occurrences),
                f"returned unexpected activitymoment {am} for expected occurrences {expected_occurrences}")

        # Same amount of occurrences/activitymoments
        self.assertEqual(len(activity_moments), len(expected_occurrences))

    def test_get_activitymoments_between_extra_start_within_bounds(self):
        """
            Tests if an occurrence with a recurrence_id outside the bounds of get_occurrences_between,
            but with a local_start_date between these same bounds, is included in the result.
        """
        recurrence_id = timezone.datetime(2020, 10, 7, 14, 0, 0, tzinfo=timezone.utc)
        self._test_get_activitymoments_between(
            [
                recurrence_id, timezone.datetime(2020, 10, 14, 14, 0, 0, tzinfo=timezone.utc)
            ],
            recurrence_id=recurrence_id,
            new_start_date=timezone.datetime(2020, 10, 13, 14, 0, 0, tzinfo=timezone.utc)
        )

    def test_get_activitymoments_between_extra_start_outside_bounds(self):
        """
            Tests if an occurrence with a recurrence_id outside the bounds of get_occurrences_between,
            and with a local_start_date also outside these same bounds, is excluded in the result.
        """
        recurrence_id = timezone.datetime(2020, 10, 7, 14, 0, 0, tzinfo=timezone.utc)
        self._test_get_activitymoments_between(
            [
                timezone.datetime(2020, 10, 14, 14, 0, 0, tzinfo=timezone.utc)
            ],
            recurrence_id=recurrence_id,
            new_start_date=timezone.datetime(2020, 11, 1, 14, 0, 0, tzinfo=timezone.utc)
        )

    def test_get_activitymoments_between_extra_end_within_bounds(self):
        """
            Tests if an occurrence with a recurrence_id outside the bounds of get_occurrences_between,
            but with a local_end_date between these same bounds, is included in the result.
        """
        recurrence_id = timezone.datetime(2020, 10, 7, 14, 0, 0, tzinfo=timezone.utc)
        self._test_get_activitymoments_between(
            [
                recurrence_id, timezone.datetime(2020, 10, 14, 14, 0, 0, tzinfo=timezone.utc)
            ],
            recurrence_id=recurrence_id,
            new_start_date=timezone.datetime(2020, 10, 1, 14, 0, 0, tzinfo=timezone.utc),
            new_end_date=timezone.datetime(2020, 10, 13, 14, 0, 0, tzinfo=timezone.utc)
        )

    def test_get_activitymoments_between_extra_wrap_bounds_just_end(self):
        """
            Tests if an occurrence with a recurrence_id outside the bounds of get_occurrences_between,
            but with a local_end_date making it wrap the bounds, is included in the result.
        """
        recurrence_id = timezone.datetime(2020, 10, 7, 14, 0, 0, tzinfo=timezone.utc)
        self._test_get_activitymoments_between(
            [
                recurrence_id, timezone.datetime(2020, 10, 14, 14, 0, 0, tzinfo=timezone.utc)
            ],
            recurrence_id=recurrence_id,
            new_end_date=timezone.datetime(2020, 10, 30, 14, 0, 0, tzinfo=timezone.utc)
        )

    def test_get_activitymoments_between_extra_wrap_bounds_start_and_end(self):
        """
            Tests if an occurrence with a recurrence_id outside the bounds of get_occurrences_between,
            but completely wrapping the bounds with a new start AND end date, is included in the result.
        """
        recurrence_id = timezone.datetime(2020, 10, 7, 14, 0, 0, tzinfo=timezone.utc)
        self._test_get_activitymoments_between(
            [
                recurrence_id, timezone.datetime(2020, 10, 14, 14, 0, 0, tzinfo=timezone.utc)
            ],
            recurrence_id=recurrence_id,
            new_start_date=timezone.datetime(2020, 10, 1, 14, 0, 0, tzinfo=timezone.utc),
            new_end_date=timezone.datetime(2020, 10, 30, 14, 0, 0, tzinfo=timezone.utc)
        )

    def test_get_activitymoments_between_extra_default_end_within_bounds(self):
        """
            Tests if an occurrence with a recurrence_id outside the bounds of get_occurrences_between,
            but with a local_start_date just before the bounds, such that the activity's default duration
            makes it end within the bounds, is included in the result.
        """
        recurrence_id = timezone.datetime(2020, 10, 7, 14, 0, 0, tzinfo=timezone.utc)
        self._test_get_activitymoments_between(
            [
                recurrence_id, timezone.datetime(2020, 10, 14, 14, 0, 0, tzinfo=timezone.utc)
            ],
            recurrence_id=recurrence_id,
            # Start half an hour before the bounds
            new_start_date=timezone.datetime(2020, 10, 9, 23, 30, 0, tzinfo=timezone.utc),
        )

    def test_get_activitymoments_between_surplus_start_outside(self):
        """
            Tests if an occurrence with a recurrence_id inside the bounds of get_occurrences_between,
            but with a local_start_date outside these same bounds, is excluded from the result.
        """
        self._test_get_activitymoments_between(
            [], new_start_date=timezone.datetime(2020, 10, 18, 14, 0, 0, tzinfo=timezone.utc),
        )

    def test_get_activitymoments_between_surplus_end_earlier(self):
        """
            Tests if an occurrence with a recurrence_id inside the bounds of get_occurrences_between,
            but with a local_end_date outside these same bounds, is excluded from the result.
        """
        self._test_get_activitymoments_between(
            [], new_end_date=timezone.datetime(2020, 10, 14, 15, 30, 0, tzinfo=timezone.utc),
            after=timezone.datetime(2020, 10, 14, 17, 0, 0, tzinfo=timezone.utc),
            before=timezone.datetime(2020, 10, 14, 23, 30, 0, tzinfo=timezone.utc)
        )

    def test_recurrence_different_day(self):
        """
            django_recurrences does not always handle recurrences around midnight correctly due to
            timezone offsets. Tests if we're using django_recurrences correctly so it simply doesn't
            encounter those problems.
            Tests an activity that starts just after midnight in CEST, but just before in UTC.
        """
        # Occurs weekly on Wednesday 12 aug, 01:30 CEST
        self.activity.start_date = timezone.datetime(2020, 8, 11, 23, 30, 0, tzinfo=timezone.utc)
        self.activity.save()

        after = timezone.datetime(2020, 8, 11, 0, 0, 0, tzinfo=timezone.utc)
        before = timezone.datetime(2020, 8, 25, 0, 0, 0, tzinfo=timezone.utc)
        recurrences = list(self.activity.get_occurrences_starting_between(after, before))

        # Should have an occurrence at the start
        self.assertIn(timezone.datetime(2020, 8, 11, 23, 30, 0, tzinfo=timezone.utc), recurrences)

        # Should have an occurrence the week after (19 aug, 01:30 CEST)
        self.assertIn(timezone.datetime(2020, 8, 18, 23, 30, 0, tzinfo=timezone.utc), recurrences)

        # Should not have other occurrences
        self.assertEqual(len(recurrences), 2)

    def test_has_occurrence_at_alt_start_time(self):
        """
            Tests if has_occurrence_at does not break if the activitymoment for that occurrence
            has a different start time
        """
        recurrence_id = timezone.datetime(2020, 10, 7, 14, 0, 0, tzinfo=timezone.utc)
        self.activity_moment = ActivityMoment.objects.get(
            parent_activity=self.activity,
            recurrence_id=recurrence_id,
        )
        # Occur later instead
        alt_start_time = timezone.datetime(2020, 10, 18, 14, 0, 0, tzinfo=timezone.utc)
        self.activity_moment.local_start_date = alt_start_time
        self.activity_moment.save()

        # Should occur at the activitymoments's recurrence_id, and not its alt start time
        self.assertTrue(self.activity.has_occurrence_at(recurrence_id))
        self.assertFalse(self.activity.has_occurrence_at(alt_start_time))


class ActivityMomentTestCase(TestCase):
    fixtures = ['test_users.json', 'test_activity_slots']

    def setUp(self):
        pass

    def test_channels_activity_attributes(self):
        moment = ActivityMoment.objects.get(id=1)

        self.assertEqual(moment.title, moment.parent_activity.title)
        self.assertEqual(moment.description, moment.parent_activity.description)
        self.assertEqual(moment.slots_image, moment.parent_activity.slots_image)
        self.assertEqual(moment.location, moment.parent_activity.location)
        self.assertEqual(moment.max_participants, moment.parent_activity.max_participants)

    def test_overwrites_activity_attributes(self):
        moment = ActivityMoment.objects.get(id=1)
        moment.local_description = "Unique description"
        moment.local_location = "Different location"
        moment.local_max_participants = 186
        moment.save()

        self.assertEqual(moment.description, "Unique description")
        self.assertEqual(moment.location, "Different location")
        self.assertEqual(moment.max_participants, 186)

    def test_overwrites_start_date(self):
        """ Tests if the start_date can be changed """
        activity_moment: ActivityMoment = ActivityMoment.objects.get(id=1)

        self.assertEqual(activity_moment.start_date, activity_moment.recurrence_id)

        new_date = timezone.datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        activity_moment.local_start_date = new_date
        self.assertEqual(activity_moment.start_date, new_date)

    def test_overwrites_end_date(self):
        """ Tests if the end_date can be changed """
        activity_moment: ActivityMoment = ActivityMoment.objects.get(id=1)
        cur_date = timezone.datetime(2020, 8, 14, 21, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(activity_moment.end_date, cur_date)

        new_date = timezone.datetime(2020, 8, 15, 23, 30, 0, tzinfo=timezone.utc)
        activity_moment.local_end_date = new_date
        self.assertEqual(activity_moment.end_date, new_date)

    def test_clean_end_date(self):
        """ Tests if the model is properly cleaned """
        # End dates cannot occur before the start date
        # #####
        activity_moment: ActivityMoment = ActivityMoment.objects.get(id=1)

        # Should not break without an end date
        activity_moment.full_clean()
        activity_moment.local_start_date = timezone.datetime(2020, 8, 15, 19, 0, 0, tzinfo=timezone.utc)
        activity_moment.full_clean()

        # Should throw an error with an end date
        new_date = timezone.datetime(2020, 8, 15, 19, 0, 0, tzinfo=timezone.utc)
        activity_moment.local_end_date = new_date

        # end_date = start_date -> invalid
        with self.assertRaisesMessage(ValidationError, "End date must be later than this occurrence's start date"):
            activity_moment.full_clean()

        # Should throw an error with an end date, but without a start_date
        new_date = timezone.datetime(2020, 8, 14, 18, 30, 0, tzinfo=timezone.utc)
        activity_moment.local_end_date = new_date
        activity_moment.local_start_date = None

        # end_date < start_date -> invalid
        with self.assertRaisesMessage(ValidationError, "End date must be later than this occurrence's start date"):
            activity_moment.full_clean()

        # Should not break if end_date > start_date
        activity_moment.local_end_date = activity_moment.recurrence_id + timezone.timedelta(hours=3)
        activity_moment.full_clean()
        activity_moment.local_start_date = activity_moment.recurrence_id + timezone.timedelta(hours=2)
        activity_moment.full_clean()

    def test_is_full(self):
        activity_moment = ActivityMoment.objects.get(id=2)
        self.assertFalse(activity_moment.is_full())
        # Set the maximum number to the amount of users is the activitymoment
        activity_moment.local_max_participants = activity_moment.participant_count
        self.assertTrue(activity_moment.is_full())
        # Check that -1 does not cause problems
        activity_moment.local_max_participants = -1
        self.assertFalse(activity_moment.is_full())

    def test_participant_count(self):
        self.assertEqual(ActivityMoment.objects.get(id=3).get_subscribed_users().count(), 2)
        self.assertEqual(ActivityMoment.objects.get(id=3).get_guest_subscriptions().count(), 3)
        self.assertEqual(ActivityMoment.objects.get(id=3).participant_count, 5)

    def test_get_subscribed_users(self):
        """ Test that get subscribed users returns the correct users """
        users = ActivityMoment.objects.get(id=1).get_subscribed_users()
        self.assertEqual(users.count(), 1)
        self.assertIsInstance(users.first(), User)
        self.assertEqual(users.first().id, 3)

        # Test that it returns multiple
        self.assertEqual(ActivityMoment.objects.get(id=2).get_subscribed_users().count(), 2)

        # This activity contains three entries, but only two users (one double entry) ensure it is not counted double
        users = ActivityMoment.objects.get(id=3).get_subscribed_users()
        self.assertEqual(users.count(), 2)
        # Also validate that it did not count user 3 that does have an external user
        self.assertNotIn(3, [user.id for user in users])
        guests_entries = ActivityMoment.objects.get(id=3).get_guest_subscriptions()
        self.assertIn(3, [entry.user_id for entry in guests_entries])

    def test_get_user_subscriptions(self):
        """ Test that user subscriptions generally return the correct data"""
        participations = ActivityMoment.objects.get(id=3).get_user_subscriptions(User.objects.get(id=1))
        self.assertEqual(participations.count(), 2)
        self.assertIsInstance(participations.first(), Participant)
        self.assertEqual(participations.first().activity_slot.parent_activity_id, 2)
        self.assertEqual(participations.last().user_id, 1)

        # AnonymousUsers return empty querysets
        self.assertEquals(ActivityMoment.objects.get(id=3).get_user_subscriptions(AnonymousUser()).count(), 0)

    def test_get_guest_subscriptions(self):
        participants = ActivityMoment.objects.get(id=3).get_guest_subscriptions()
        self.assertEqual(participants.count(), 3)
        self.assertIsInstance(participants.first(), Participant)
        self.assertEqual(participants.first().activity_slot.parent_activity_id, 2)

    def test_get_slots(self):
        slots = ActivityMoment.objects.get(id=3).get_slots()
        self.assertEqual(slots.count(), 5)
        self.assertIn(ActivitySlot.objects.get(title='Pandemic'), slots)
        self.assertIn(ActivitySlot.objects.get(title='Boardgame the Boardgame'), slots)

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_is_open_for_subscriptions(self, mock_tz):
        self.assertFalse(ActivityMoment.objects.get(id=3).is_open_for_subscriptions())
        self.assertTrue(ActivityMoment.objects.get(id=1).is_open_for_subscriptions())


class ActivitySlotTestCase(TestCase):
    fixtures = ['test_users.json', 'test_activity_slots']

    def test_get_subscribed_users(self):
        slot = ActivitySlot.objects.get(id=4)
        self.assertEqual(
            slot.get_subscribed_users().count(),
            0
        )
        slot = ActivitySlot.objects.get(id=8)
        self.assertEqual(
            slot.get_subscribed_users().count(),
            2
        )
        self.assertIsInstance(slot.get_subscribed_users().first(), User)

    def test_get_subscribed_guests(self):
        slot = ActivitySlot.objects.get(id=4)
        self.assertEqual(
            slot.get_guest_subscriptions().count(),
            3
        )
        self.assertIsInstance(slot.get_guest_subscriptions().first(), Participant)

        slot = ActivitySlot.objects.get(id=8)
        self.assertEqual(
            slot.get_guest_subscriptions().count(),
            0
        )

    def test_clean_recurrence_id_omitted(self):
        slot = ActivitySlot(
            title='test_recurrentce_clean',
            parent_activity_id=1,
        )

        with self.assertRaises(ValidationError) as error:
            slot.clean_fields()
        self.assertIn('recurrence_id', error.exception.error_dict.keys())

    def test_clean_recurrence_id_invalid(self):
        slot = ActivitySlot(
            title='test_recurrentce_clean',
            parent_activity_id=1,
            recurrence_id="2020-08-15T19:00:00Z"
        )   # There is no activity_moment on this recurrence moment

        with self.assertRaises(ValidationError) as error:
            slot.clean_fields()
        self.assertIn('recurrence_id', error.exception.error_dict.keys())

        slot = ActivitySlot(
            title='test_recurrentce_clean',
            parent_activity_id=1,
            recurrence_id="2020-08-14T19:00:00Z"
        )
        # Recurrence_id is valid, so it does not raise an error
        slot.clean_fields()


class ActivityParticipantTestCase(TestCase):
    fixtures = ['test_users.json', 'test_members', 'test_activity_slots']

    @patch('core.models.ExtendedUser.get_display_name', return_value='trigger_test')
    def test_str(self, mock_function=None):
        participation = Participant.objects.create(
            user_id=1,
            activity_slot_id=7
        )
        # The method that should be triggered is overwritten as output is tested elsewhere
        # We merely need to assure that it is used
        self.assertEqual(str(participation), 'trigger_test')

        participation.guest_name = 'some guest'
        self.assertEqual(str(participation), participation.guest_name + ' (ext)')

    def test_manager_filter_guests_only(self):
        self.assertEqual(
            Participant.objects.filter_guests_only().count(),
            Participant.objects.exclude(guest_name='').count()
        )

    def test_manager_filter_users_only(self):
        self.assertEqual(
            Participant.objects.filter_users_only().count(),
            Participant.objects.filter(guest_name='').count()
        )




