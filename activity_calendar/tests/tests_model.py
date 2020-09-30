from collections import Counter
from datetime import datetime

from django.contrib.auth.models import AnonymousUser
from django.core.validators import ValidationError
from django.conf import settings
from django.utils.http import urlencode
from django.test import TestCase, Client
from django.utils import timezone
from recurrence import Recurrence, deserialize as deserialize_recurrence_test
from unittest.mock import patch

from .tests_views import mock_now

from activity_calendar.models import Activity, ActivitySlot, Participant
from core.models import ExtendedUser as User

# Tests model properties related to fetching participants, slots, etc.
class ModelMethodsTest(TestCase):
    fixtures = ['test_users.json', 'test_activity_methods']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.filter(username='test_user').first()
        self.client.force_login(self.user)
        
        self.activity = Activity.objects.get(id=2)
        self.simple_activity = Activity.objects.get(id=1)

        self.upcoming_occurence_date = datetime.fromisoformat('2020-08-19T14:00:00').replace(tzinfo=timezone.utc)

    # Should provide the correct url if the activity has an image, or the default image if no image is given
    def test_image_url(self):
        self.assertEqual(self.activity.image_url, f"{settings.MEDIA_URL}images/presets/rpg.jpg")

        self.activity.image = None
        self.assertEqual(self.activity.image_url, f"{settings.STATIC_URL}images/activity_default.png")

    # Should obtain the subscribed participants (possibly with duplicates if someone subscribed more than once)
    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_get_subscribed_participants(self, mock_tz):
        # Should get correctly for recurring activities
        participants = list(map(lambda x: x['user_id'],
                self.activity.get_subscribed_participants(recurrence_id=self.upcoming_occurence_date).values('user_id')))
        self.assertEqual(len(participants), 3)
        participants = Counter(participants)
        self.assertEqual(participants.get(1), 2)
        self.assertEqual(participants.get(2), 1)
        
        # Should get correctly for non-recurring activities
        participants = list(map(lambda x: x['user_id'],
                self.simple_activity.get_subscribed_participants().values('user_id')))
        self.assertEqual(len(participants), 2)
        participants = Counter(participants)
        self.assertEqual(participants.get(1), 1)
        self.assertEqual(participants.get(2), 1)

        # Should throw a TypeError if no recurrence-id is given for a recurring activity
        with self.assertRaises(TypeError) as error:
            self.activity.get_subscribed_participants()
    
    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_get_num_subscribed_participants(self, mock_tz):
        # Recurring activity
        self.assertEqual(self.activity.get_num_subscribed_participants(recurrence_id=self.upcoming_occurence_date), 3)
        # Non-recurring activity
        self.assertEqual(self.simple_activity.get_num_subscribed_participants(), 2)
    
    def test_get_max_num_participants(self):
        # Finite slots, more slots can be created, infinite participants
        self.assertEqual(self.simple_activity.get_max_num_participants(), -1)

        # Finite slots, more slots can be created, finite participants
        self.simple_activity.max_participants = 12
        self.assertEqual(self.simple_activity.get_max_num_participants(), 12)

        # Finite slots, no more slots can be created, infinite participants
        # Fixture slot can have at most 6 participants
        self.simple_activity.max_participants = -1
        self.simple_activity.slot_creation = "CREATION_NONE"
        self.assertEqual(self.simple_activity.get_max_num_participants(), 6)

        # Finite slots, no more slots can be created (there are already 5), infinite participants
        self.simple_activity.slot_creation = "CREATION_AUTO"
        for _ in range(4):
            ActivitySlot.objects.create(title='Filler', max_participants=2, parent_activity=self.simple_activity)
        self.assertEqual(self.simple_activity.get_max_num_participants(), 4*2 + 6)

        # Finite slots, no more slots can be created (there are already 5), finite participants
        # Max participants is higher than the slots' max participants
        self.simple_activity.max_participants = 70
        self.assertEqual(self.simple_activity.get_max_num_participants(), 4*2 + 6)

        # Finite slots, no more slots can be created (there are already 5), infinite participants for at least 1 slot
        self.simple_activity.max_participants = -1
        ActivitySlot.objects.exclude(title='Filler').update(max_participants=-1)
        self.assertEqual(self.simple_activity.get_max_num_participants(), -1)

        # Finite slots, no more slots can be created (there are already 5), finite participants
        # Max participants is higher than the slots' max participants
        self.simple_activity.max_participants = 2
        self.assertEqual(self.simple_activity.get_max_num_participants(), 2)

    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_get_slots(self, mock_tz):
        # Should get correctly for recurring activities
        slots = list(map(lambda x: x['id'],
                self.activity.get_slots(recurrence_id=self.upcoming_occurence_date).values('id')))
        self.assertEqual(len(slots), 2)
        slots = Counter(slots)
        self.assertEqual(slots.get(2), 1)
        self.assertEqual(slots.get(3), 1)
        
        # Should get correctly for non-recurring activities
        slots = list(map(lambda x: x['id'],
                self.simple_activity.get_slots().values('id')))
        self.assertEqual(len(slots), 1)
        slots = Counter(slots)
        self.assertEqual(slots.get(1), 1)

        # Should throw a TypeError if no recurrence-id is given for a recurring activity
        with self.assertRaises(TypeError) as error:
            self.activity.get_slots()

    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_get_num_slots(self, mock_tz):
        # Recurring activity
        self.assertEqual(self.activity.get_num_slots(recurrence_id=self.upcoming_occurence_date), 2)
        # Non-recurring activity
        self.assertEqual(self.simple_activity.get_num_slots(), 1)

    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_get_max_num_slots(self, mock_tz):
        # Cannot create slots; work with the already existing slots
        self.assertEqual(self.activity.get_max_num_slots(recurrence_id=self.upcoming_occurence_date), 2)

        # Slots can be created by users/are created automatically; limited by activity's maximum number of slots
        self.assertEqual(self.simple_activity.get_max_num_slots(), 5)

    def test_can_user_create_slot(self):
        # User is already registered for a slot, limited registrations, can have more participants
        self.assertFalse(self.simple_activity.can_user_create_slot(self.user))

        # User is already registered for a slot, unlimited registrations, can have more participants
        Participant.objects.filter(user=self.user).delete()
        self.simple_activitymax_slots_join_per_participant = -1
        self.assertTrue(self.simple_activity.can_user_create_slot(self.user))

        # User is not already registered for a slot, limited registrations, cannot have more participants
        Participant.objects.filter(user=self.user).delete()
        self.simple_activity.max_participants = 0
        self.simple_activitymax_slots_join_per_participant = 1
        self.assertFalse(self.simple_activity.can_user_create_slot(self.user))

        # User is not already registered for a slot, limited registrations, can have more participants
        self.simple_activity.max_participants = -1
        self.assertTrue(self.simple_activity.can_user_create_slot(self.user))

        # Infinte slots, unlimited registrations, can have more participants
        self.simple_activity.max_slots = -1
        self.simple_activity.max_slots_join_per_participant = -1
        self.assertTrue(self.simple_activity.can_user_create_slot(self.user))
        
        # Passing values ourselves (finite slots, unlimited registrations)
        self.simple_activity.max_slots = 5
        self.assertTrue(self.simple_activity.can_user_create_slot(self.user,
                num_slots=3, num_user_registrations=2, num_total_participants=3, num_max_participants=10))

    @patch('django.utils.timezone.now', side_effect=mock_now)
    def test_get_user_subscriptions(self, mock_tz):
        # Not passing values ourselves
        participants = list(map(lambda x: x['user_id'],
                self.activity.get_user_subscriptions(self.user, recurrence_id=self.upcoming_occurence_date).values('user_id')))
        self.assertEqual(len(participants), 1)
        participants = Counter(participants)
        self.assertEqual(participants.get(2), 1)

        # Passing values ourselves
        participants = list(map(lambda x: x['user_id'],
                self.activity.get_user_subscriptions(self.user, recurrence_id=self.upcoming_occurence_date,
                        participants=Participant.objects.all()).values('user_id')))
        self.assertEqual(len(participants), 2)
        participants = Counter(participants)
        self.assertEqual(participants.get(2), 2)

        # Anonymous User
        participants = list(map(lambda x: x['user_id'],
                self.activity.get_user_subscriptions(AnonymousUser(), recurrence_id=self.upcoming_occurence_date).values('user_id')))
        self.assertEqual(len(participants), 0)


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

    # Must do nothing if everything is defined correctly
    def test_clean_correct(self):
        self.base_activity.clean_fields()

        self.base_activity.recurrences = deserialize_recurrence_test("RDATE:19700101T230000Z")
        self.base_activity.clean_fields()
