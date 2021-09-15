import datetime

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import dateparse
from django.forms import ModelForm

from unittest.mock import patch

from activity_calendar.models import *
from activity_calendar.forms import *
from core.models import ExtendedUser as User
from core.tests.util import suppress_warnings

from utils.testing import FormValidityMixin
from . import mock_now


class ActivityFormValidationMixin(FormValidityMixin):
    fixtures = ['test_users.json', 'test_activity_slots.json']

    def setUp(self):
        self.user = User.objects.filter(username='test_user').first()
        self.activity = Activity.objects.get(id=self.activity_id)
        if isinstance(self.recurrence_id, str):
            self.recurrence_id = dateparse.parse_datetime(self.recurrence_id)

        self.activity_moment = ActivityMoment.objects.get_or_create(
            parent_activity_id=self.activity.id,
            recurrence_id=self.recurrence_id,
        )[0]

    def get_form_kwargs(self, **kwargs):
        kwargs = super(ActivityFormValidationMixin, self).get_form_kwargs(**kwargs)
        # Reload activity_moment as we may have made changes to its cached parent object
        self.activity_moment.refresh_from_db()
        kwargs.update({
            'user': self.user,
            'activity': self.activity,
            'recurrence_id': self.recurrence_id,
            'activity_moment': self.activity_moment,
        })
        return kwargs


class RegisterForActivityFormTestCase(ActivityFormValidationMixin, TestCase):
    """ Tests the RegisterForActivityForm """
    form_class = RegisterForActivityForm
    activity_id = 1
    recurrence_id = "2020-08-14T19:00:00Z"

    def test_has_fields(self):
        """ Test that the fields contain the minimally defined fields """
        self.assertHasField('sign_up')

    @patch('django.utils.timezone.now', side_effect=mock_now(datetime.datetime(2020, 8, 5, 0, 0)))
    def test_closed_sign_up_early(self, mock_tz):
        """ Test that the form invalidates when subscriptions are not open yet"""
        self.assertFormHasError({'sign_up': True}, code='closed')

    @patch('django.utils.timezone.now', side_effect=mock_now(datetime.datetime(2020, 8, 15, 0, 0)))
    def test_closed_sign_up_late(self, mock_tz):
        """ Test that the form invalidates when subscriptions are already closed"""
        self.assertFormHasError({'sign_up': True}, code='closed')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_opened_sign_up(self, mock_tz):
        """ Tests that the form validates for normal situations """
        self.assertFormValid({'sign_up': True})

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_max_capacity_sign_in(self, mock_tz):
        """ Test that the form invalidates when maximum is reached before signing in """
        self.activity.max_participants = 1
        # There should be 1 participant already
        self.activity.save()
        self.assertEqual(1, self.activity_moment.get_subscribed_users().count())

        self.assertFormHasError({'sign_up': True}, code='activity-full')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_max_capacity_offset_in_activity_moment(self, mock_tz):
        # The local TestMoment should overwrite max participants if desired
        self.assertFormValid({'sign_up': True})
        self.activity_moment.local_max_participants = 0
        self.activity_moment.save()
        self.assertFormHasError({'sign_up': True}, code='activity-full')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_max_capacity_sign_out(self, mock_tz):
        """ Test that the form validates when maximum is reached, but the user is signing out"""
        self.activity.max_participants = 2
        # There should be 1 participant already
        self.activity.save()
        Participant.objects.create(user=self.user, activity_slot_id=1)
        self.assertEqual(2, self.activity_moment.get_subscribed_users().count())

        self.assertFormValid({'sign_up': False})

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_slot_mode(self, mock_tz):
        """ Tests that form invalidates when slot creation mode is not CREATION_AUTO """
        self.activity.slot_creation = Activity.SLOT_CREATION_STAFF
        self.activity.save()
        self.assertFormHasError({'sign_up': True}, code='invalid_slot_mode')

        self.activity.slot_creation = Activity.SLOT_CREATION_USER
        self.activity.save()
        self.assertFormHasError({'sign_up': True}, code='invalid_slot_mode')

        self.activity.slot_creation = Activity.SLOT_CREATION_AUTO
        self.activity.save()
        self.assertFormValid({'sign_up': True})

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_not_registered(self, mock_tz):
        """ Tests form invalidates when signing out when not registered """
        self.assertFormHasError({'sign_up': False}, code='not-registered')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_already_registered(self, mock_tz):
        """ Tests that the form invalidates when user is attempting registering on already registered list"""
        Participant.objects.create(user=self.user, activity_slot_id=1)
        self.assertFormHasError({'sign_up': True}, code='already-registered')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_save_sign_up_existing_slot(self, mock_tz):
        """ Checks if the user is registered to any of the already existing slots"""
        self.assertGreater(self.activity_moment.get_slots().count(), 0)
        form = self.assertFormValid({'sign_up': True})
        self.assertEqual(0, self.activity_moment.get_user_subscriptions(self.user).count())
        form.save()
        self.assertEqual(1, self.activity_moment.get_user_subscriptions(self.user).count())

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_save_sign_up_new_slot(self, mock_tz):
        """ Checks if a new slot is made when no slots are present """
        # Remove all (1) current slots on this activity
        self.activity.activity_slot_set.all().delete()

        form = self.assertFormValid({'sign_up': True})
        self.assertEqual(0, self.activity_moment.get_user_subscriptions(self.user).count())
        form.save()
        self.assertEqual(1, self.activity_moment.get_user_subscriptions(self.user).count())

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_save_sign_out(self, mock_tz):
        """ Test saving a sign-out action """
        Participant.objects.create(user=self.user, activity_slot_id=1)
        form = self.assertFormValid({'sign_up': False})
        self.assertEqual(1, self.activity_moment.get_user_subscriptions(self.user).count())
        form.save()
        self.assertEqual(0, self.activity_moment.get_user_subscriptions(self.user).count())


class RegisterForActivitySlotFormTestCase(ActivityFormValidationMixin, TestCase):
    """ Tests the RegisterForActivityForm """
    form_class = RegisterForActivitySlotForm
    activity_id = 2
    recurrence_id = "2020-08-12T14:00:00Z"

    def test_has_fields(self):
        """ Test that the fields contain the minimally defined fields """
        self.assertHasField('slot_id')
        self.assertHasField('sign_up')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_required_fields(self, mock_tz):
        """ Test that the user input contains at least the required fields """
        self.assertFormHasError({'sign_up': True}, code='required', field='slot_id')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_slot_not_found(self, mock_tz):
        # Activity and slot do not match
        self.assertFormHasError({'sign_up': True, 'slot_id': 1}, code='slot-not-found')
        # Slot does not exist
        self.assertFormHasError({'sign_up': True, 'slot_id': 12}, code='slot-not-found')

    @patch('django.utils.timezone.now', side_effect=mock_now(datetime.datetime(2020, 8, 5, 0, 0)))
    def test_closed_sign_up_early(self, mock_tz):
        """ Test that the form invalidates when subscriptions are not open yet"""
        self.assertFormHasError({'sign_up': True, 'slot_id': 7}, code='closed')

    @patch('django.utils.timezone.now', side_effect=mock_now(datetime.datetime(2020, 8, 15, 0, 0)))
    def test_closed_sign_up_late(self, mock_tz):
        """ Test that the form invalidates when subscriptions are already closed"""
        self.assertFormHasError({'sign_up': True, 'slot_id': 7}, code='closed')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_opened_sign_up(self, mock_tz):
        """ Tests that the form validates for normal situations """
        self.assertFormValid({'sign_up': True, 'slot_id': 7})

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_max_capacity_sign_in(self, mock_tz):
        """ Test that the form invalidates when maximum is reached before signing in """
        self.activity.max_participants = 2
        # There should be 2 participant already
        self.activity.save()
        self.assertEqual(2, self.activity_moment.get_subscribed_users().count())

        self.assertFormHasError({'sign_up': True, 'slot_id': 7}, code='activity-full')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_max_capacity_sign_out(self, mock_tz):
        """ Test that the form validates when maximum is reached, but the user is signing out"""
        self.activity.max_participants = 3
        # There should be 1 participant already
        self.activity.save()
        Participant.objects.create(user=self.user, activity_slot_id=7)
        self.assertEqual(3, self.activity_moment.get_subscribed_users().count())

        self.assertFormValid({'sign_up': False, 'slot_id': 7})

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_max_capacity_offset_in_activity_moment(self, mock_tz):
        # The local TestMoment should overwrite max participants if desired
        self.assertFormValid({'sign_up': True, 'slot_id': 7})
        self.activity_moment.local_max_participants = 0
        self.activity_moment.save()
        self.assertFormHasError({'sign_up': True, 'slot_id': 7}, code='activity-full')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_already_registered(self, mock_tz):
        """ Tests that the form invalidates when user is attempting registering on already registered list"""
        Participant.objects.create(user=self.user, activity_slot_id=7)
        self.assertFormHasError({'sign_up': True, 'slot_id': 7}, code='already-registered')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_not_registered(self, mock_tz):
        """ Tests form invalidates when signing out when not registered """
        self.assertFormHasError({'sign_up': False, 'slot_id': 7}, code='not-registered')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_slot_full_sign_in(self, mock_tz):
        self.assertFormHasError({'sign_up': True, 'slot_id': 8}, code='slot-full')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_slot_full_sign_out(self, mock_tz):
        Participant.objects.create(user=self.user, activity_slot_id=8)
        self.assertFormValid({'sign_up': False, 'slot_id': 8})

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_user_max_slots_occupied(self, mock_tz):
        Participant.objects.create(user=self.user, activity_slot_id=8)
        self.assertFormHasError({'sign_up': True, 'slot_id': 7}, code='max-slots-occupied')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_save_sign_up(self, mock_tz):
        """ Checks if the user is registered to any of the already existing slots"""
        form = self.assertFormValid({'sign_up': True, 'slot_id': 7})
        slot = ActivitySlot.objects.get(id=7)
        self.assertFalse(slot.get_subscribed_users().filter(id=self.user.id).exists())
        form.save()
        self.assertTrue(slot.get_subscribed_users().filter(id=self.user.id).exists())

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_save_sign_out(self, mock_tz):
        """ Checks if the user is registered to any of the already existing slots"""
        Participant.objects.create(user=self.user, activity_slot_id=7)
        form = self.assertFormValid({'sign_up': False, 'slot_id': 7})
        slot = ActivitySlot.objects.get(id=7)
        self.assertTrue(slot.get_subscribed_users().filter(id=self.user.id).exists())
        form.save()
        self.assertFalse(slot.get_subscribed_users().filter(id=self.user.id).exists())


class RegisterNewSlotFormTestCase(ActivityFormValidationMixin, TestCase):
    """ Tests the RegisterForActivityForm """
    form_class = RegisterNewSlotForm
    activity_id = 2
    recurrence_id = "2020-08-12T14:00:00Z"

    def test_has_fields(self):
        """ Test that the fields contain the minimally defined fields """
        self.assertHasField('title')
        self.assertHasField('description')
        self.assertHasField('max_participants')
        self.assertHasField('sign_up')

    @patch('django.utils.timezone.now', side_effect=mock_now(datetime.datetime(2020, 8, 5, 0, 0)))
    def test_closed_sign_up_early(self, mock_tz):
        """ Test that the form invalidates when subscriptions are not open yet"""
        self.assertFormHasError({'sign_up': True, 'title': 'My slot', 'max_participants': -1}, code='closed')

    @patch('django.utils.timezone.now', side_effect=mock_now(datetime.datetime(2020, 8, 15, 0, 0)))
    def test_closed_sign_up_late(self, mock_tz):
        """ Test that the form invalidates when subscriptions are already closed"""
        self.assertFormHasError({'sign_up': True, 'title': 'My slot', 'max_participants': -1}, code='closed')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_opened_sign_up(self, mock_tz):
        """ Tests that the form validates for normal situations """
        self.assertFormValid({'sign_up': True, 'title': 'My slot', 'max_participants': -1})

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_max_capacity_sign_in(self, mock_tz):
        """ Test that the form invalidates when maximum number of occupants is reached """
        self.activity.max_participants = 2
        # There should be 2 participant already
        self.activity.save()
        self.assertEqual(2, self.activity_moment.get_subscribed_users().count())

        self.assertFormHasError({'sign_up': True, 'title': 'My slot', 'max_participants': -1}, code='activity-full')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_max_capacity_offset_in_activity_moment(self, mock_tz):
        # The local TestMoment should overwrite max participants if desired
        self.assertFormValid({'sign_up': True, 'title': 'My slot', 'max_participants': -1})
        self.activity_moment.local_max_participants = 0
        self.activity_moment.save()
        self.assertFormHasError({'sign_up': True, 'title': 'My slot', 'max_participants': -1}, code='activity-full')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_required_fields(self, mock_tz):
        """ Test that the user input contains at least the required fields """
        self.assertFormHasError({'sign_up': True, 'max_participants': -1}, code='required', field='title')
        self.assertFormHasError({'sign_up': True, 'title': 'My slot'}, code='required', field='max_participants')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_slot_mode(self, mock_tz):
        """ Tests that form invalidates when slot creation mode is not CREATION_AUTO """
        self.activity.slot_creation = Activity.SLOT_CREATION_STAFF
        self.activity.save()
        self.assertFormHasError({'sign_up': True, 'title': 'My slot', 'max_participants': -1}, code='user-slot-creation-denied')

        self.activity.slot_creation = Activity.SLOT_CREATION_AUTO
        self.activity.save()
        self.assertFormHasError({'sign_up': True, 'title': 'My slot', 'max_participants': -1}, code='user-slot-creation-denied')

        self.activity.slot_creation = Activity.SLOT_CREATION_USER
        self.activity.save()
        self.assertFormValid({'sign_up': True, 'title': 'My slot', 'max_participants': -1})

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_slot_mode_admin_override(self, mock_tz):
        """ Tests that form validates when admin creates a slot when slot mode is CREATION_NONE """
        self.activity.slot_creation = Activity.SLOT_CREATION_STAFF
        self.activity.save()
        self.user.user_permissions.add(Permission.objects.get(codename='can_ignore_none_slot_creation_type'))
        self.user.save()
        self.assertFormValid({'sign_up': True, 'title': 'My slot', 'max_participants': -1})

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_local_slot_mode(self, mock_tz):
        """
            Tests that form validates when an activity_moment overrides slot creation to (dis)allow
            it, while it is normally (dis)allowed
        """
        # Slot creation normally not allowed; it is allowed now
        self.activity.slot_creation = Activity.SLOT_CREATION_STAFF
        self.activity.save()
        self.activity_moment.local_slot_creation = Activity.SLOT_CREATION_USER
        self.activity_moment.save()
        self.assertFormValid({'sign_up': True, 'title': 'My slot', 'max_participants': -1})

        # Slot creation normally allowed; it is disallowed now
        self.activity.slot_creation = Activity.SLOT_CREATION_USER
        self.activity.save()
        self.activity_moment.local_slot_creation = Activity.SLOT_CREATION_STAFF
        self.activity_moment.save()
        self.assertFormHasError({'sign_up': True, 'title': 'My slot', 'max_participants': -1}, code='user-slot-creation-denied')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_user_max_slots_occupied(self, mock_tz):
        """ Tests that the form fails when user already occupies the maximum number of slots """
        Participant.objects.create(user=self.user, activity_slot_id=8)
        self.assertFormHasError({'sign_up': True, 'title': 'My slot', 'max_participants': -1}, code='max-slots-occupied')
        # If user does not join the slot
        self.assertFormValid({'sign_up': False, 'title': 'My slot', 'max_participants': -1})

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_max_slots_claimed(self, mock_tz):
        self.activity.max_slots = 2
        self.activity.save()
        self.assertFormHasError({'sign_up': True, 'title': 'My slot', 'max_participants': -1}, code='max-slots-claimed')

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_save_form_creation(self, mock_tz):
        """ Checks that a slot is created with the given parameters """
        form = self.assertFormValid({
            'sign_up': True,
            'title': 'My slot',
            'max_participants': -1,
            'description': "Some various text about my slot"})
        slot_query = ActivitySlot.objects.filter(
            parent_activity=self.activity,
            recurrence_id=self.recurrence_id,
            title='My slot'
        )
        self.assertFalse(slot_query.exists())
        form.save()
        self.assertTrue(slot_query.exists())

        # Analyse slot model
        slot = slot_query.first()
        self.assertEqual(slot.owner, self.user)
        self.assertEqual(slot.max_participants, -1)
        self.assertEqual(slot.description, "Some various text about my slot")

        # Test that the user is registered as participant
        self.assertEqual(slot.get_subscribed_users().first(), self.user)

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_save_form_creation_without_user(self, mock_tz):
        """ Checks that a slot is created with the given parameters """
        form = self.assertFormValid({
            'sign_up': False,
            'title': 'Some slot',
            'max_participants': -1,
            'description': "Some various text about this slot"})
        slot_query = ActivitySlot.objects.filter(
            parent_activity=self.activity,
            recurrence_id=self.recurrence_id,
            title='Some slot'
        )
        self.assertFalse(slot_query.exists())
        form.save()
        self.assertTrue(slot_query.exists())

        # Analyse slot model
        slot = slot_query.first()
        self.assertEqual(slot.owner, self.user)
        self.assertEqual(slot.max_participants, -1)
        self.assertEqual(slot.description, "Some various text about this slot")

        # Test that there are no users registered to the slot
        self.assertEqual(slot.get_subscribed_users().count(), 0)


class ActivityMomentFormTestCase(FormValidityMixin, TestCase):
    form_class = ActivityMomentForm
    fixtures = ['test_users.json', 'test_activity_slots.json']

    def setUp(self):
        self.activity_moment = ActivityMoment.objects.first()
        self.form = ActivityMomentForm(instance=self.activity_moment, data={})

    def test_fields(self):
        self.assertNotIn('recurrence_id', self.form.fields.keys())
        self.assertNotIn('parent_activity', self.form.fields.keys())
        self.assertIn('local_title', self.form.fields.keys())
        self.assertIn('local_description', self.form.fields.keys())
        self.assertIn('local_location', self.form.fields.keys())
        self.assertIn('local_max_participants', self.form.fields.keys())

    def test_saves_moment_without_id(self):
        """ Tests that it saves non-db-existing activitymoments to the database """
        activity_moment = ActivityMoment(
            parent_activity_id=1,
            recurrence_id = "2020-08-28T19:00:00Z",
        )
        form = ActivityMomentForm(instance=activity_moment, data={})
        form.save()
        self.assertTrue(ActivityMoment.objects.filter(
            parent_activity_id=1,
            recurrence_id = "2020-08-28T19:00:00Z",
        ).exists())

    def test_validity_check(self):
        """ Tests that normal form data is valid """
        self.assertFormValid({
            'local_title': 'Different title',
            'local_description': 'Different description',
            'local_location': 'Different location',
            'local_max_participants': 8,
        }, instance=self.activity_moment)

    def test_requires_instance(self):
        """ Form requires an instnace given. Or at least, it should. """
        try:
            self.form_class(data={})
        except KeyError:
            pass
        else:
            raise AssertionError("Form did not require instance (of activity_moment)")

    def test_django_inheritance(self):
        """ Test that it inherits from the correct class (thus assuming inheritence consistency) """
        self.assertIsInstance(self.form, ModelForm)




