import datetime

from django.test import TestCase, Client
from django.conf import settings
from django.utils import timezone, dateparse
from django.utils.http import urlencode

from activity_calendar.models import ActivitySlot, Activity, Participant
from core.models import ExtendedUser as User
from core.util import suppress_warnings

##################################################################################
# Test cases for the activity views
# @since 29 AUG 2020
##################################################################################


# Source: https://stackoverflow.com/a/6558571
def next_weekday(d, weekday):
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0: # Target day already happened this week
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)

# Tests for the Admin Panel
class ActivityAdminTest(TestCase):
    fixtures = ['test_users.json', 'test_activity_slots.json']

    @classmethod
    def setUpTestData(self):
        self.upcoming_occurence_date = next_weekday(timezone.now(), 2).replace(hour=14, minute=0, second=0, microsecond=0)
        self.encoded_upcoming_occurence_date = urlencode({'date': self.upcoming_occurence_date.isoformat()})

    def setUp(self):
        self.client = Client()
        self.user = User.objects.filter(username='test_user').first()
        self.client.force_login(self.user)
        
        # Ensure that all dates are in the future (and subscriptions are open)
        ActivitySlot.objects.filter(parent_activity__id=2).update(recurrence_id=self.upcoming_occurence_date)

    @suppress_warnings
    def test_get_slots_invalid_dates(self):
        # No recurrence_id given
        response = self.client.get('/calendar/slots/2', data={})
        self.assertEqual(response.status_code, 404)

        # No occurence at the given date
        response = self.client.get('/calendar/slots/2?date=2020-09-03T14%3A00%3A00.000Z', data={})
        self.assertEqual(response.status_code, 404)

    def test_get_slots_valid_date(self):
        # Valid (occurence) date given
        response = self.client.get('/calendar/slots/2?' + self.encoded_upcoming_occurence_date, data={})
        self.assertEqual(response.status_code, 200)
        
        context = response.context
        
        self.assertEqual(context['activity'].title, 'Boardgame Evening')
        self.assertEqual(context['recurrence_id'], self.upcoming_occurence_date)
        self.assertFalse(context['deregister'])

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
        self.assertEqual(context['max_participants'], 30)
        self.assertEqual(context['num_registered_slots'], 1)

        # Cannot create a slot as user is already subscribed to a slot
        self.assertFalse(context['can_create_slot'])
        self.assertTrue(context['subscriptions_open'])

        # No dummy slots as slot_creation = CREATION_USER
        self.assertEqual(context['num_dummy_slots'], 0)

    # Tests whether the correct number of dummy slots are created
    def test_dummy_slots(self):
        # Infinite dummy slots
        response = self.client.get('/calendar/slots/1?date=2020-08-14T19%3A00%3A00.000Z', data={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['num_dummy_slots'], Activity.MAX_NUM_AUTO_DUMMY_SLOTS)

        activity = Activity.objects.get(title='Single')
        activity.max_slots = 1
        activity.save()
        slot = ActivitySlot(title='Slot Title', parent_activity=activity)

        # No more dummy slots should be created (as one already exists!)
        response = self.client.get('/calendar/slots/1?date=2020-08-14T19%3A00%3A00.000Z', data={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['num_dummy_slots'], 0)


    # Test POST without a correct url
    # Even if the data is invalid, we expect a 400 bad request
    @suppress_warnings
    def test_invalid_post_url(self):
        # No recurrence_id given
        response = self.client.post('/calendar/slots/2', data={})
        self.assertEqual(response.status_code, 400)

        # No occurence at the given date
        response = self.client.post('/calendar/slots/2?date=2020-09-03T14%3A00%3A00.000Z', data={})
        self.assertEqual(response.status_code, 400)

    # Test POST without invalid POST data
    @suppress_warnings
    def test_invalid_post_data(self):
        old_count = ActivitySlot.objects.all().count()

        # Cannot create slots without a title
        response = self.client.post('/calendar/slots/2?' + self.encoded_upcoming_occurence_date, data={
            # title is missing
            'max_participants': -1,
        })
        self.assertEqual(response.status_code, 200)

        # Number of slots should not have increased
        self.assertEqual(old_count, ActivitySlot.objects.all().count())

        # Cannot create slots with 0 participants
        response = self.client.post('/calendar/slots/2?' + self.encoded_upcoming_occurence_date, data={
            'title': 'Cool!',
            'max_participants': 0,
        })
        self.assertEqual(response.status_code, 200)
        
        # Number of slots should not have increased
        self.assertEqual(old_count, ActivitySlot.objects.all().count())

    def test_valid_post_data(self):
        # Clear all participant objects first so they cannot interfere
        Participant.objects.filter(user=self.user).delete()
        response = self.client.post('/calendar/slots/2?' + self.encoded_upcoming_occurence_date, data={
            'title': 'My new Slot',
            'max_participants': 5,
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        # Number of slots should not have increased
        self.assertIsNotNone(ActivitySlot.objects.filter(title='My new Slot',
                owner=self.user, max_participants=5,
                parent_activity__id=2).first())
    

    def test_valid_register(self):
        Participant.objects.filter(user=self.user).delete()
        response = self.client.post('/api/calendar/register/2', data={}, follow=True)
        self.assertEqual(response.status_code, 200)

        # Should have a new participant
        self.assertIsNotNone(Participant.objects.filter(user=self.user,
                activity_slot__id=2).first())

    def test_valid_deregister(self):
        response = self.client.post('/api/calendar/deregister/6', data={}, follow=True)
        self.assertEqual(response.status_code, 200)

        # Participant should no longer exist
        self.assertIsNone(Participant.objects.filter(user=self.user,
                activity_slot__id=6).first())

        # Should have a deregister message
        self.assertTrue(response.context['deregister'])

    # Test if unauthenticated users are redirected to the login page
    @suppress_warnings
    def test_must_be_authenticated(self):
        self.client.logout()
        response = self.client.post('/api/calendar/register/6', data={})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?next=/api/calendar/register/6')

        response = self.client.post('/api/calendar/deregister/6', data={})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?next=/api/calendar/deregister/6')

        response = self.client.post('/calendar/slots/2?' + self.encoded_upcoming_occurence_date, data={
            'title': 'My new Slot',
            'max_participants': 5,
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?' + urlencode({'next': '/calendar/slots/2?' + self.encoded_upcoming_occurence_date}))
