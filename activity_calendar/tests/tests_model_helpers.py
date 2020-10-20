from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

from activity_calendar.models import Activity, ActivitySlot, Participant
from core.models import ExtendedUser as User

from . import mock_now

##################################################################################
# Test the Activity and related models' helper methods
# @since 29 AUG 2020
##################################################################################

class ActivityRelatedModelHelpersTest(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        activity_data = {
            'id': 4,
            'title': 'Wow',
            # Start/end dates are during CET (UTC+1)
            # Start dt: 01 JAN 2020, 15.00 (CET)
            'start_date': timezone.datetime(2020, 1, 1, 14, 0, 0, tzinfo=timezone.utc),
            'end_date': timezone.datetime(2020, 1, 1, 18, 0, 0, tzinfo=timezone.utc),
            'recurrences': "RRULE:FREQ=WEEKLY;BYDAY=TU"
        }
        
        self.activity = Activity(**activity_data)
        self.slot = ActivitySlot(id=1, parent_activity=self.activity, title="Wow2")

    # Tests the display method of Activity
    def test_activity_display(self):
        self.assertEqual(str(self.activity), "Wow (recurring)")

    # Tests the display method of ActivitySlot
    def test_activityslot_display(self):
        self.assertEqual(str(self.slot), "Wow2")

    # Tests the display method of a Participant
    def test_participant_display(self):
        participant = Participant(activity_slot=self.slot, user=User.objects.filter(username="test_user").first())
        self.assertEqual(str(participant), participant.user.get_simple_display_name())

    @patch('django.utils.timezone.now', side_effect=mock_now(timezone.datetime(2020, 3, 20, 0, 0)))
    def test_has_occurence_at_same_dst(self, mock_tz):
        pass

    @patch('django.utils.timezone.now', side_effect=mock_now(timezone.datetime(2020, 3, 20, 0, 0)))
    def test_CET_has_occurence_at_CET_to_CEST(self, mock_tz):
        """
            Query an activity ocurrence when
            - that activity's first occurence was in CET
            - our current timezone is in CET
            - the queried occurence is in CEST
        """
        query_dt = timezone.make_aware(timezone.datetime(2020, 3, 31, 15, 0, 0), timezone.pytz.timezone("Europe/Amsterdam"))

        has_occurence_at_query_dt = self.activity.has_occurence_at(query_dt)
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

        has_occurence_at_query_dt = self.activity.has_occurence_at(query_dt)
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

        has_occurence_at_query_dt = self.activity.has_occurence_at(query_dt)
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

        has_occurence_at_query_dt = self.activity.has_occurence_at(query_dt)
        self.assertTrue(has_occurence_at_query_dt)
