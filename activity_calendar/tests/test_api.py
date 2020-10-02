import datetime

from django.test import TestCase, Client
from django.conf import settings
from django.utils import timezone, dateparse
from django.utils.http import urlencode
from unittest.mock import patch

from activity_calendar.models import ActivitySlot, Activity, Participant
from core.models import ExtendedUser as User
from core.util import suppress_warnings

##################################################################################
# Test cases for the activity views
# @since 29 AUG 2020
##################################################################################

def mock_now():
    dt = datetime.datetime(2020, 8, 14, 0, 0)
    return timezone.make_aware(dt)

# Tests for the Admin Panel
class TestActivityAPI(TestCase):
    # Note: the API is currently unused, but could be used if wanted to.
    fixtures = ['test_users.json', 'test_activity_slots.json']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.filter(username='test_user').first()
        self.client.force_login(self.user)


    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_valid_register(self, mock_tz):
        Participant.objects.filter(user=self.user).delete()

        # Recurring activity
        response = self.client.post('/api/calendar/register/2', data={}, follow=True)
        self.assertEqual(response.status_code, 200)

        # Should have a new participant
        self.assertIsNotNone(Participant.objects.filter(user=self.user,
                                                        activity_slot__id=2).first())

        # Non-recurring activity
        response = self.client.post('/api/calendar/register/1', data={}, follow=True)
        self.assertEqual(response.status_code, 200)

        # Should have a new participant
        self.assertIsNotNone(Participant.objects.filter(user=self.user,
                                                        activity_slot__id=1).first())

    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_valid_deregister(self, mock_tz):
        # Recurring activity
        response = self.client.post('/api/calendar/deregister/6', data={}, follow=True)
        self.assertEqual(response.status_code, 200)

        # Participant should no longer exist
        self.assertIsNone(Participant.objects.filter(user=self.user,
                                                     activity_slot__id=6).first())

        # Non-recurring activity
        Participant.objects.create(user=self.user, activity_slot=ActivitySlot.objects.get(id=1))
        response = self.client.post('/api/calendar/deregister/1', data={}, follow=True)
        self.assertEqual(response.status_code, 200)

        # Participant should no longer exist
        self.assertIsNone(Participant.objects.filter(user=self.user,
                                                     activity_slot__id=1).first())

        self.assertRedirects(response, "/calendar/activity/1/?date=2020-08-14T19%3A00%3A00%2B00%3A00&deregister=True")

    # Test if unauthenticated users are redirected to the login page
    @suppress_warnings
    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_must_be_authenticated(self, mock_tz):
        self.client.logout()
        response = self.client.post('/api/calendar/register/6', data={})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?next=/api/calendar/register/6')

        response = self.client.post('/api/calendar/deregister/6', data={})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?next=/api/calendar/deregister/6')

        response = self.client.post('/calendar/activity/2/?date=2020-08-19T14%3A00%3A00.000Z', data={
            'title': 'My new Slot',
            'max_participants': 5,
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?' + urlencode({'next': '/calendar/activity/2/?date=2020-08-19T14%3A00%3A00.000Z'}))

