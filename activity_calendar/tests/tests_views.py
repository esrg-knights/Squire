import datetime

from django.test import TestCase, Client
from django.utils import timezone
from unittest.mock import patch

from activity_calendar.models import ActivitySlot, Activity, Participant
from core.models import ExtendedUser as User
from core.util import suppress_warnings

from . import mock_now

##################################################################################
# Test cases for the activity views
# @since 29 AUG 2020
##################################################################################

# Tests for the Admin Panel
class ActivityAdminTest(TestCase):
    fixtures = ['test_users.json', 'test_activity_slots.json']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.filter(username='test_user').first()
        self.client.force_login(self.user)

    @suppress_warnings
    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_get_slots_invalid_dates(self, mock_tz):
        # No recurrence_id given
        response = self.client.get('/calendar/activity/2/', data={})
        self.assertEqual(response.status_code, 404)

        # No occurence at the given date
        response = self.client.get('/calendar/activity/2/?date=2020-09-03T14%3A00%3A00.000Z', data={})
        self.assertEqual(response.status_code, 404)

    @patch('django.utils.timezone.now', side_effect=mock_now(datetime.datetime(2020, 8, 15, 0, 0)))
    def test_get_slots_valid_date(self, mock_tz):
        # Valid (occurence) date given
        response = self.client.get('/calendar/activity/2/?date=2020-08-19T14%3A00%3A00.000Z', data={})
        self.assertEqual(response.status_code, 200)

        context = response.context

        self.assertEqual(context['activity'].title, 'Boardgame Evening')
        self.assertEqual(context['recurrence_id'], datetime.datetime.fromisoformat('2020-08-19T14:00:00').replace(tzinfo=timezone.utc))

        slots = []
        for slot in context['slot_list']:
            slots.append(slot.title)

        self.assertEqual(len(slots), 5)
        self.assertIn('Terraforming Mars', slots)
        self.assertIn('Ticket to Ride', slots)
        self.assertIn('Pandemic', slots)
        self.assertIn('Betrayal', slots)
        self.assertIn('Boardgame the Boardgame', slots)

        self.assertEqual(context['num_total_participants'], 3)

        # Cannot create a slot as user is already subscribed to a slot
        self.assertTrue(context['subscriptions_open'])


    # Test POST without a correct url
    # Even if the data is invalid, we expect a 400 bad request
    @suppress_warnings
    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_invalid_post_url(self, mock_tz):
        # No recurrence_id given
        response = self.client.post('/calendar/activity/2/', data={})
        self.assertEqual(response.status_code, 404)

        # No occurence at the given date
        response = self.client.post('/calendar/activity/2/?date=2020-09-03T14%3A00%3A00%2B00%3A00', data={})
        self.assertEqual(response.status_code, 404)

    @patch('django.utils.timezone.now', side_effect=mock_now(datetime.datetime(2020, 8, 15, 0, 0)))
    def test_valid_post_data_recurring(self, mock_tz):
        # Clear all participant objects first so they cannot interfere
        Participant.objects.filter(user=self.user).delete()
        response = self.client.post('/calendar/activity/2/create_slot/?date=2020-08-19T14%3A00%3A00%2B00%3A00', data={
            'title': 'My new Slot',
            'max_participants': 5,
        }, follow=True)

        # New slot should exist
        new_slot = ActivitySlot.objects.filter(title='My new Slot',
                                               owner=self.user, max_participants=5,
                                               parent_activity__id=2).first()
        self.assertIsNotNone(new_slot)

        # Assert that it redirects to the desired page
        self.assertRedirects(response, '/calendar/activity/2/?date=2020-08-19T14%3A00%3A00%2B00%3A00')
