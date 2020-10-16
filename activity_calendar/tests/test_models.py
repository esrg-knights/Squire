from datetime import datetime

from django.contrib.auth.models import AnonymousUser
from django.core.validators import ValidationError
from django.conf import settings
from django.test import TestCase, Client
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


class ActivityMomentTestCase(TestCase):
    fixtures = ['test_users.json', 'test_activity_slots']

    def setUp(self):
        pass

    def test_channels_activity_attributes(self):
        moment = ActivityMoment.objects.get(id=1)

        self.assertEqual(moment.title, moment.parent_activity.title)
        self.assertEqual(moment.description, moment.parent_activity.description)
        self.assertEqual(moment.image, moment.parent_activity.image)
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

    def test_get_subscribed_users(self):
        """ Test that get subscribed users returns the correct users """
        users = ActivityMoment.objects.get(id=1).get_subscribed_users()
        self.assertEqual(users.count(), 1)
        self.assertIsInstance(users.first(), User)
        self.assertEqual(users.first().id, 3)

        # Test that it returns multiple
        self.assertEqual(ActivityMoment.objects.get(id=2).get_subscribed_users().count(), 2)

        # This activity contains three entries, but only two users (one double entry) ensure it is not counted double
        self.assertEqual(ActivityMoment.objects.get(id=3).get_subscribed_users().count(), 2)

    def test_get_user_subscriptions(self):
        """ Test that user subscriptions generally return the correct data"""
        participations = ActivityMoment.objects.get(id=3).get_user_subscriptions(User.objects.get(id=1))
        self.assertEqual(participations.count(), 2)
        self.assertIsInstance(participations.first(), Participant)
        self.assertEqual(participations.first().activity_slot.parent_activity_id, 2)
        self.assertEqual(participations.last().user_id, 1)

        # AnonymousUsers return empty querysets
        self.assertEquals(ActivityMoment.objects.get(id=3).get_user_subscriptions(AnonymousUser()).count(), 0)

    def test_get_slots(self):
        slots = ActivityMoment.objects.get(id=3).get_slots()
        self.assertEqual(slots.count(), 5)
        self.assertIn(ActivitySlot.objects.get(title='Pandemic'), slots)
        self.assertIn(ActivitySlot.objects.get(title='Boardgame the Boardgame'), slots)

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_is_open_for_subscriptions(self, mock_tz):
        self.assertFalse(ActivityMoment.objects.get(id=3).is_open_for_subscriptions())
        self.assertTrue(ActivityMoment.objects.get(id=1).is_open_for_subscriptions())





