import datetime
import json

from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from activity_calendar.models import Activity

from . import mock_now

##################################################################################
# Test cases for the activity views
# @since 29 AUG 2020
##################################################################################


class UpcomingCoreActivitiesTest(TestCase):
    """
    Tests for the upcoming core activities API.
    These tests assume that alternative start dates, RDATES, EXDATES, etc. are
    already properly accounted for by Activity.get_next_activitymoment(..)
    """

    fixtures = ["activity_calendar/test_activity_coregroupings.json"]

    def setUp(self):
        self.url = reverse("activity_calendar:upcoming_core_feed")

    def _get_activity_json(self, **kwargs):
        """Fetches activity data from the returned JSON"""
        res = self.client.get(self.url, kwargs)
        self.assertEqual(res.status_code, 200)

        jsonres = json.loads(res.content)
        if "activities" not in jsonres:
            self.fail("Malformed json returned; Expected 'activities' to be in the root of the json object")
        return jsonres["activities"]

    def _is_activity_in_json(self, activity_title, json, start_date=None, core_grouping_identifier=None):
        """
        Returns whether an activitymoment with the given title (and optionally starting at a specific date,
        and/or being part of a specific core grouping)
        is in the json
        """
        if start_date is not None:
            start_date = datetime.datetime.fromisoformat(start_date)

        for activity in json:
            if (
                activity["title"] == activity_title
                and (start_date is None or datetime.datetime.fromisoformat(activity["start"]) == start_date)
                and (
                    core_grouping_identifier is None
                    or activity["core_grouping_identifier"] == core_grouping_identifier
                )
            ):
                return True
        return False

    def assertActivityInJSON(self, activity_title, json, start_date=None, core_grouping_identifier=None):
        """
        Raises an AssertionError if the given activity (optionally starting at a specific datetime,
        and/or being part of a specific core grouping) is not in the json
        """
        if not self._is_activity_in_json(
            activity_title, json, start_date=start_date, core_grouping_identifier=core_grouping_identifier
        ):
            self.fail(f"{activity_title} ({start_date}) was not located in the JSON activitylist: {json}")

    def assertActivityNotInJSON(self, activity_title, json, start_date=None, core_grouping_identifier=None):
        """
        Raises an AssertionError if the given activity (optionally starting at a specific datetime,
        and/or being part of a specific core grouping) is in the json
        """
        if self._is_activity_in_json(
            activity_title, json, start_date=start_date, core_grouping_identifier=core_grouping_identifier
        ):
            self.fail(f"{activity_title} ({start_date}) was unexpectedly located in the JSON activitylist: {json}")

    @patch("django.utils.timezone.now", side_effect=mock_now(datetime.datetime(2021, 12, 21, 0, 0)))
    def test_groups_multiple(self, _):
        """Tests if multiple activities are returned if multiple core groupings are passed"""
        activities = self._get_activity_json(groups="boardgames,roleplay")

        self.assertActivityInJSON(
            "Boardgame Evening",
            activities,
            start_date="2021-12-21T19:00:00+00:00",
            core_grouping_identifier="boardgames",
        )
        self.assertActivityInJSON(
            "Open Roleplay Evening",
            activities,
            start_date="2021-12-22T19:00:00+00:00",
            core_grouping_identifier="roleplay",
        )
        self.assertEqual(len(activities), 2, f"There should've only been two activities in the json: {activities}")

    @patch("django.utils.timezone.now", side_effect=mock_now(datetime.datetime(2021, 12, 21, 0, 0)))
    def test_groups_ordering(self, _):
        """Tests if the ordering of the core groupings passed in the request matters"""
        activities = self._get_activity_json(groups="boardgames,roleplay")
        self.assertEqual(
            activities[0]["title"],
            "Boardgame Evening",
            "'Boardgame Evening' should be the first returned item as its core grouping was passed first",
        )
        self.assertEqual(
            activities[1]["title"],
            "Open Roleplay Evening",
            "'Open Roleplay Evening' should be the first returned item as its core grouping was passed second",
        )

        self.assertEqual(activities[0]["core_grouping_identifier"], "boardgames")
        self.assertEqual(activities[1]["core_grouping_identifier"], "roleplay")

        # Reverse order
        activities = self._get_activity_json(groups="roleplay,boardgames")
        self.assertEqual(
            activities[0]["title"],
            "Open Roleplay Evening",
            "'Open Roleplay Evening' should be the first returned item as its core grouping was passed first",
        )
        self.assertEqual(
            activities[1]["title"],
            "Boardgame Evening",
            "'Boardgame Evening' should be the first returned item as its core grouping was passed second",
        )

        self.assertEqual(activities[0]["core_grouping_identifier"], "roleplay")
        self.assertEqual(activities[1]["core_grouping_identifier"], "boardgames")

    @patch("django.utils.timezone.now", side_effect=mock_now(datetime.datetime(2021, 12, 21, 0, 0)))
    def test_groups_skip(self, _):
        """
        Tests if activities that do not have matching core groupings (different or none at all)
        than the request are ignored.
        """
        activities = self._get_activity_json(groups="boardgames")
        self.assertActivityNotInJSON("Roleplay Evening", activities)
        self.assertActivityNotInJSON("Swordfighting Training", activities)

    @patch("django.utils.timezone.now", side_effect=mock_now(datetime.datetime(2021, 12, 28, 0, 0)))
    def test_skips_cancelled_removed_moments(self, _):
        """Tests if removed or cancelled activitymoments are skipped"""
        # Get rid of earlier occurrences of other activities with the same grouping
        Activity.objects.filter(title="Tabletop Lunch").delete()

        activities = self._get_activity_json(groups="boardgames")
        # Boardgame evening on the 28th is cancelled
        self.assertActivityNotInJSON("Boardgame Evening", activities, start_date="2021-12-28T19:00:00+00:00")

        # Boardgame evening on the 4th is removed
        self.assertActivityNotInJSON("Boardgame Evening", activities, start_date="2022-01-04T19:00:00+00:00")

        # Boardgame evening on the 11th continues as usual
        self.assertActivityInJSON(
            "Boardgame Evening",
            activities,
            start_date="2022-01-11T19:00:00+00:00",
            core_grouping_identifier="boardgames",
        )

    @patch("django.utils.timezone.now", side_effect=mock_now(datetime.datetime(2023, 1, 1, 0, 0)))
    def test_skips_empty_coregrouping(self, _):
        """Tests if coregroupings without (valid) activities are skipped"""
        # Roleplay Evenings end in 2022 (so there is no next occurrence);
        # There are no activities for the 'foo' grouping (in fact, the 'foo' grouping does not even exist)
        activities = self._get_activity_json(groups="roleplay,foo")
        self.assertFalse(activities)

    def test_earliest_occurrence_multiple_activities(self):
        """Tests if the earliest ocurrence of multiple activities with the same core grouping is returned"""
        # The boardgame evening occurs before the tabletop lunch
        with patch("django.utils.timezone.now", side_effect=mock_now(datetime.datetime(2021, 12, 21, 0, 0))):
            activities = self._get_activity_json(groups="boardgames")
            self.assertActivityInJSON("Boardgame Evening", activities, start_date="2021-12-21T19:00:00+00:00")

        # The tabletop lunch occurs before the boardgame evening
        with patch("django.utils.timezone.now", side_effect=mock_now(datetime.datetime(2021, 12, 22, 0, 0))):
            activities = self._get_activity_json(groups="boardgames")
            self.assertActivityInJSON("Tabletop Lunch", activities, start_date="2021-12-22T12:00:00+00:00")
