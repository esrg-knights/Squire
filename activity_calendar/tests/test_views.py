import datetime

from django.test import TestCase, Client
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Permission
from django.test.utils import override_settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.views.generic import ListView

from unittest.mock import patch

from activity_calendar.models import *
from activity_calendar.views import CreateSlotView, ActivityMomentWithSlotsView, ActivitySimpleMomentView,\
    EditActivityMomentView, ActivityOverview
from activity_calendar.forms import *

from core.models import ExtendedUser as User
from core.tests.util import suppress_warnings
from utils.testing.view_test_utils import ViewValidityMixin

from . import mock_now

##################################################################################
# Test cases for the activity views
# @since 29 AUG 2020
##################################################################################

class TestActivityViewMixin:
    fixtures = ['test_users.json', 'test_activity_slots.json']
    default_activity_id = 2
    default_iso_dt = '2020-08-12T14:00:00+00:00'
    default_url_name = None

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(username='new_user')
        self.client.force_login(self.user)

        self.recurrence_id = datetime.datetime.fromisoformat(self.default_iso_dt)
        self.activity = Activity.objects.get(id=self.default_activity_id)

        self.base_url = reverse('activity_calendar:'+self.default_url_name, kwargs={
            'activity_id': self.default_activity_id,
            'recurrence_id': datetime.datetime.fromisoformat(self.default_iso_dt),
        })
        super(TestActivityViewMixin, self).setUp()

    def build_get_response(self, iso_dt=None, url_name=None, activity_id=None, follow=False):
        return self._build_response("get", iso_dt=iso_dt, url_name=url_name, activity_id=activity_id, follow=follow)

    def build_post_response(self, data, iso_dt=None, url_name=None, activity_id=None, follow=False):
        return self._build_response("post", iso_dt=iso_dt, url_name=url_name, activity_id=activity_id, follow=follow, data=data)

    def _build_response(self, method, iso_dt=None, url_name=None, activity_id=2, follow=False, data={}):
        url_name = url_name or self.default_url_name
        iso_dt = iso_dt or self.default_iso_dt
        activity_id = activity_id or self.default_activity_id

        return getattr(self.client, method)(reverse('activity_calendar:'+url_name, kwargs={
            'activity_id': activity_id,
            'recurrence_id': datetime.datetime.fromisoformat(iso_dt),
        }), data=data, follow=follow)

    @staticmethod
    def assertHasMessage(response, level=None, text=None, print_all=False):
        """
        Assert that the response contains a specific message
        :param response: The response object
        :param level: The level of the message (messages.SUCCESS/ EROOR or custom...)
        :param text: (part of) the message string that it should contain
        :param print_all: prints all messages encountered useful to trace errors if present
        :return: Raises AssertionError if not asserted
        """
        for message in response.context['messages']:
            if print_all:
                print(message)
            if message.level == level or level is None:
                if text is None or str(text) in message.message:
                    return

        if level or text:
            msg = "There was no message for the given criteria: "
            if level:
                msg += f"level: '{level}' "
            if text:
                msg += f"text: '{text}' "
        else:
            msg = "There was no message"

        raise AssertionError(msg)


# Tests for the Admin Panel
class ActivityAdminTest(TestCase):
    fixtures = ['test_users.json', 'test_activity_slots.json']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.filter(username='test_user').first()
        self.client.force_login(self.user)

        self.base_url = reverse('activity_calendar:activity_slots_on_day', kwargs={
            'activity_id': 2,
            'recurrence_id': datetime.datetime.fromisoformat('2020-08-19T14:00:00').replace(tzinfo=timezone.utc),
        })

    @suppress_warnings
    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_get_slots_invalid_dates(self, mock_tz):
        # No recurrence_id given
        response = self.client.get('/calendar/activity/2//', data={})
        self.assertEqual(response.status_code, 404)

        # No occurence at the given date
        non_matching_dt = datetime.datetime.fromisoformat('2020-08-20T14:00:00').replace(tzinfo=timezone.utc)
        response = self.client.get(
            reverse('activity_calendar:activity_slots_on_day',
                    kwargs={'activity_id': 2, 'recurrence_id': non_matching_dt}),
            data={})
        self.assertEqual(response.status_code, 404)

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_get_slots_valid_date(self, mock_tz):
        # Valid (occurence) date given
        response = self.client.get(self.base_url, data={})
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

        self.assertEqual(context['num_total_participants'], 5)

    # Test POST without a correct url
    # Even if the data is invalid, we expect a 400 bad request
    @suppress_warnings
    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_invalid_post_url(self, mock_tz):
        # No recurrence_id given
        response = self.client.post('/calendar/activity/2/', data={})
        self.assertEqual(response.status_code, 404)

        # No occurence at the given date
        response = self.client.post('/calendar/activity/2/2020-09-03T14%3A00%3A00%2B00%3A00/', data={})
        self.assertEqual(response.status_code, 404)


class TestActivityOverview(ViewValidityMixin, TestCase):
    fixtures = ['test_users.json', 'test_activity_slots.json']
    base_user_id = 2

    def get_base_url(self, content_type=None, item_id=None):
        return reverse('activity_calendar:activity_upcoming')

    def test_class(self):
        self.assertTrue(issubclass(ActivityOverview, ListView))
        self.assertEqual(ActivityOverview.template_name, "activity_calendar/activity_overview.html")
        self.assertEqual(ActivityOverview.context_object_name, 'activities')

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_template_context(self, mock_tz):
        response  = self.client.get(self.get_base_url(item_id=1), data={})
        context = response.context

        self.assertEqual(len(context['activities']), 2)
        self.assertIsInstance(context['activities'][0], ActivityMoment)


class ActivitySimpleViewTest(TestActivityViewMixin, TestCase):
    default_url_name = "activity_slots_on_day"
    default_activity_id = 1
    default_iso_dt = '2020-08-14T19:00:00+00:00'

    def test_base_class_values(self):
        self.assertEqual(ActivitySimpleMomentView.form_class, RegisterForActivityForm)
        self.assertEqual(ActivitySimpleMomentView.template_name, "activity_calendar/activity_page_no_slots.html")

        # Test errror messages
        self.assertIn('activity-full', ActivitySimpleMomentView.error_messages)
        self.assertIn('already-registered', ActivitySimpleMomentView.error_messages)
        self.assertIn('not-registered', ActivitySimpleMomentView.error_messages)
        self.assertIn('closed', ActivitySimpleMomentView.error_messages)

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_normal_get_page(self, mock_tz):
        # The basic set-up is valid. User can create a slot
        response = self.build_get_response()
        self.assertEqual(response.status_code, 200)

        # Test standard context attributes
        self.assertEqual(response.context['activity'].id, self.default_activity_id)
        self.assertEqual(response.context['recurrence_id'], self.recurrence_id)
        self.assertEqual(response.context['subscriptions_open'], True)
        self.assertIn('subscribed_users', response.context)
        self.assertIn('subscribed_guests', response.context)
        self.assertIn('num_max_participants', response.context)
        self.assertIn('form', response.context)
        self.assertIn('show_participants', response.context)
        self.assertEqual(response.context['user_subscriptions'].exists(), False)
        self.assertEqual(response.context['num_total_participants'], 1)

        # Test template name
        self.assertEqual(response.template_name[0], ActivitySimpleMomentView.template_name)

        # Test form attributes
        self.assertIsInstance(response.context['form'], RegisterForActivityForm)
        self.assertTrue(response.context['form'].data['sign_up'])
        self.assertContains(response, "Register")
        self.assertNotContains(response, "Deregister")

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_normal_get_page_signed_up(self, mock_tz):
        # Add the user
        slot = ActivitySlot.objects.get(
            parent_activity_id=self.default_activity_id,
            recurrence_id=self.recurrence_id,
        )
        Participant.objects.create(
            activity_slot=slot,
            user=self.user,
        )

        response = self.build_get_response()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].data['sign_up'])
        self.assertContains(response, "Deregister")
        self.assertNotContains(response, "Register")

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_successful_post(self, mock_tz):
        response = self.build_post_response({
            'sign_up': True,
        }, follow=True)

        self.assertRedirects(response, self.base_url) # Should redirect to prevent resending the post on page refresh
        self.assertTrue(ActivityMoment(
            parent_activity_id=self.default_activity_id,
            recurrence_id=self.recurrence_id,
        ).get_user_subscriptions(self.user).exists())

        self.assertTrue(ActivitySlot.objects.filter().exists())
        msg = _("You have succesfully been added to '{activity_name}'").format(activity_name="Single")
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)

        # And now unsubscribe
        response = self.build_post_response({
            'sign_up': False,
        }, follow=True)

        self.assertRedirects(response, self.base_url) # Should redirect to prevent resending the post on page refresh
        self.assertFalse(ActivityMoment(
            parent_activity_id=self.default_activity_id,
            recurrence_id=self.recurrence_id,
        ).get_user_subscriptions(self.user).exists())

        self.assertTrue(ActivitySlot.objects.filter().exists())
        msg = _("You have successfully been removed from '{activity_name}'").format(activity_name="Single")
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_invalid_post(self, mock_tz):
        # Can not unsubscribe from an activity you are not regitered to.
        response = self.build_post_response({
            'sign_up': False,
        }, follow=True)

        self.assertRedirects(response, self.base_url) # Should redirect to prevent resending the post on page refresh
        self.assertTrue(ActivitySlot.objects.filter().exists())
        self.assertHasMessage(response,
                              level=messages.ERROR,
                              text=ActivitySimpleMomentView.error_messages['not-registered'])

    @patch('django.utils.timezone.now', side_effect=mock_now(datetime.datetime(2020, 8, 25, 0, 0)))
    def test_outdated_activity(self, mock_tz):
        # The basic set-up is valid. User can create a slot
        response = self.build_get_response()
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context['subscriptions_open'], False)

    def _verify_show_participants(self, recurrence_id, permissions, should_show_participants):
        # Grant relevant permission and remove others
        self.user.user_permissions.clear()
        self.user.save()
        self.user.user_permissions.add(*permissions)

        # Modify activity start/end time
        self.activity.start_date = datetime.datetime.fromisoformat(recurrence_id)
        self.activity.end_date = self.activity.start_date + datetime.timedelta(hours=2)
        self.activity.save()

        response = self.build_get_response(iso_dt=recurrence_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['show_participants'], should_show_participants)

    @patch('django.utils.timezone.now', side_effect=mock_now())
    @override_settings(AUTHENTICATION_BACKENDS=('django.contrib.auth.backends.ModelBackend',))
    def test_show_participants(self, mock_tz):
        """
            Tests if activity participants show only to users with the relevant permissions
        """
        before_perm = Permission.objects.get(codename='can_view_activity_participants_before')
        during_perm = Permission.objects.get(codename='can_view_activity_participants_during')
        after_perm = Permission.objects.get(codename='can_view_activity_participants_after')

        # User does NOT have the relevant permission to view registrations
        self._verify_show_participants(self.default_iso_dt, [during_perm, after_perm], False)
        self._verify_show_participants('2020-08-10T21:00:00+00:00', [before_perm, after_perm], False)
        self._verify_show_participants('2020-08-01T00:00:00+00:00', [before_perm, during_perm], False)

        # User HAS the relevant permission to view registrations
        self._verify_show_participants(self.default_iso_dt, [before_perm], True)
        self._verify_show_participants('2020-08-10T21:00:00+00:00', [during_perm], True)
        self._verify_show_participants('2020-08-01T00:00:00+00:00', [after_perm], True)

    def test_activitymoment_alt_start_date_text(self):
        """ Tests which text appear for activity moments that have a different start_date than their
            occurrence
        """
        recurrence_id = timezone.datetime(2020, 8, 14, 19, 0, 0, tzinfo=timezone.utc)
        self.activity_moment = ActivityMoment.objects.get(
            parent_activity=self.activity,
            recurrence_id=recurrence_id,
        )

        # If the activitymoment does not have an alt start time, no extra text should be added
        response = self.build_get_response(iso_dt=recurrence_id.isoformat())
        self.assertNotContains(response, "Replacement for the same activity on", status_code=200)
        self.assertNotContains(response, "than normal!")

        # Occurs at a different day
        self.activity_moment.local_start_date = timezone.datetime(2020, 8, 15, 14, 0, 0, tzinfo=timezone.utc)
        self.activity_moment.save()
        response = self.build_get_response(iso_dt=recurrence_id.isoformat())
        self.assertContains(response, "Replacement for the same activity on", status_code=200)

        # Occurson the same day (earlier)
        self.activity_moment.local_start_date = recurrence_id - timezone.timedelta(hours=1)
        self.activity_moment.save()
        response = self.build_get_response(iso_dt=recurrence_id.isoformat())
        self.assertContains(response, "than normal!", status_code=200)
        self.assertContains(response, "earlier")


        # Occurson the same day (later)
        self.activity_moment.local_start_date = recurrence_id + timezone.timedelta(hours=1)
        self.activity_moment.save()
        response = self.build_get_response(iso_dt=recurrence_id.isoformat())
        self.assertContains(response, "than normal!", status_code=200)
        self.assertContains(response, "later")



class ActivitySlotViewTest(TestActivityViewMixin, TestCase):
    default_url_name = "activity_slots_on_day"
    default_activity_id = 2
    default_iso_dt = '2020-08-12T14:00:00+00:00'

    def test_base_class_values(self):
        self.assertEqual(ActivityMomentWithSlotsView.form_class, RegisterForActivitySlotForm)
        self.assertEqual(ActivityMomentWithSlotsView.template_name, "activity_calendar/activity_page_slots.html")

        # Test errror messages
        self.assertIn('activity-full', ActivityMomentWithSlotsView.error_messages)
        self.assertIn('already-registered', ActivityMomentWithSlotsView.error_messages)
        self.assertIn('not-registered', ActivityMomentWithSlotsView.error_messages)
        self.assertIn('closed', ActivityMomentWithSlotsView.error_messages)
        self.assertIn('max-slots-occupied', ActivityMomentWithSlotsView.error_messages)
        self.assertIn('slot-full', ActivityMomentWithSlotsView.error_messages)
        # Errors related to create slot form which can be entered on this page too (though is processed elsewhere)
        self.assertIn('max-slots-claimed', ActivityMomentWithSlotsView.error_messages)
        self.assertIn('user-slot-creation-denied', ActivityMomentWithSlotsView.error_messages)

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_normal_get_page(self, mock_tz):
        # The basic set-up is valid. User can create a slot
        response = self.build_get_response()
        self.assertEqual(response.status_code, 200)

        # Test standard context attributes
        self.assertEqual(response.context['activity'].id, self.default_activity_id)
        self.assertEqual(response.context['recurrence_id'], self.recurrence_id)
        self.assertEqual(response.context['subscriptions_open'], True)
        self.assertEqual(response.context['user_subscriptions'].exists(), False)
        self.assertEqual(response.context['num_total_participants'], 2)
        self.assertIn('slot_list', response.context)
        self.assertIn('show_participants', response.context)
        self.assertIn('slot_creation_form', response.context)

        self.assertIsInstance(response.context['slot_creation_form'], RegisterNewSlotForm)

        # Test template name
        self.assertEqual(response.template_name[0], ActivityMomentWithSlotsView.template_name)

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_get_page_slot_mode(self, mock_tz):
        # User can create slots, as all users can create slots for it
        # User should also be automatically signed up for it
        response = self.build_get_response()
        self.assertEqual(response.status_code, 200)
        self.assertIn('slot_creation_form', response.context)
        self.assertIsInstance(response.context['slot_creation_form'], RegisterNewSlotForm)
        self.assertTrue(response.context['slot_creation_form'].initial.get('sign_up'))

        # User cannot create slots, as it does not have the relevant permissions
        self.activity.slot_creation = Activity.SLOT_CREATION_STAFF
        self.activity.save()
        response = self.build_get_response()
        self.assertEqual(response.status_code, 200)
        self.assertIn('slot_creation_form', response.context)
        self.assertIsNone(response.context['slot_creation_form'])

        # User can create slots, as it has the relevant permission
        # User should NOT automatically be signed up for it
        self.user.user_permissions.add(Permission.objects.get(codename='can_ignore_none_slot_creation_type'))
        response = self.build_get_response()
        self.assertEqual(response.status_code, 200)
        self.assertIn('slot_creation_form', response.context)
        self.assertIsInstance(response.context['slot_creation_form'], RegisterNewSlotForm)
        self.assertFalse(response.context['slot_creation_form'].initial.get('sign_up'))


    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_normal_get_page_signed_up(self, mock_tz):
        # Add the user
        slot = ActivitySlot.objects.filter(
            parent_activity_id=self.default_activity_id,
            recurrence_id=self.recurrence_id,
        ).first()
        Participant.objects.create(
            activity_slot=slot,
            user=self.user,
        )

        response = self.build_get_response()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"You are subscribed to slot '{slot.title}'")

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_successful_post(self, mock_tz):
        response = self.build_post_response({
            'sign_up': True,
            'slot_id': 7,
        }, follow=True)

        self.assertRedirects(response, self.base_url) # Should redirect to prevent resending the post on page refresh
        self.assertTrue(Participant.objects.filter(activity_slot_id=7, user=self.user).exists())

        self.assertTrue(ActivitySlot.objects.filter().exists())
        msg = _("You have succesfully been added to '{activity_name}'").format(activity_name="Liberty the boardgame")
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)

        # And now unsubscribe
        response = self.build_post_response({
            'sign_up': False,
            'slot_id': 7,
        }, follow=True)

        self.assertRedirects(response, self.base_url) # Should redirect to prevent resending the post on page refresh
        self.assertFalse(Participant.objects.filter(activity_slot_id=7, user=self.user).exists())

        self.assertTrue(ActivitySlot.objects.filter().exists())
        msg = _("You have successfully been removed from '{activity_name}'").format(activity_name="Liberty the boardgame")
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_invalid_post(self, mock_tz):
        # Can not unsubscribe from an activity you are not registered to.
        response = self.build_post_response({
            'sign_up': True,
            'slot_id': 8
        }, follow=True)

        self.assertRedirects(response, self.base_url) # Should redirect to prevent resending the post on page refresh
        self.assertTrue(ActivitySlot.objects.filter().exists())
        self.assertHasMessage(response,
                              level=messages.ERROR,
                              text=ActivityMomentWithSlotsView.error_messages['slot-full'])


    # Tests in which cases a user can view private slot locations
    def test_private_slot_locations(self):
        # Add some private slot locations
        self.activity.private_slot_locations = True
        self.activity.save()

        slots = ActivitySlot.objects.filter(
            parent_activity_id=self.default_activity_id,
            recurrence_id=self.recurrence_id,
        )
        for slot in slots:
            slot.location = f"Secret Location #{slot.id}"
            slot.save()

        # Should not be able to see private slot locations (not registered, no permission)
        response = self.build_get_response()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hidden until registered for this slot", count=len(slots))
        self.assertContains(response, "Secret Location #", count=0)

        # Should only be able to see private slot location of slots a user is registered for
        first_slot = slots.first()
        Participant.objects.create(
            activity_slot=first_slot,
            user=self.user,
        )
        # Refresh so the participant entry is updated on this model
        first_slot.refresh_from_db()

        response = self.build_get_response()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hidden until registered for this slot", count=len(slots)-1)
        self.assertContains(response, f"Secret Location #{first_slot.id}", count=1)

        # Should be able to see all private slot locations with the relevant
        #   permission, regardless of registration status
        view_private_perm = Permission.objects.get(codename='can_view_private_slot_locations')
        self.user.user_permissions.clear()
        self.user.save()
        self.user.user_permissions.add(view_private_perm)

        response = self.build_get_response()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hidden until registered for this slot", count=0)
        self.assertContains(response, "Secret Location #", count=len(slots))


class CreateSlotViewTest(TestActivityViewMixin, TestCase):
    default_url_name = "create_slot"
    default_activity_id = 2
    default_iso_dt = '2020-08-12T14:00:00+00:00'

    @suppress_warnings
    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_get_slots_invalid_dates(self, mock_tz):
        # No occurence at the given date
        response = self.build_get_response(iso_dt='2020-08-17T14:00:00+00:00')
        self.assertEqual(response.status_code, 404)

        # Occureance is of a different activity
        response = self.build_get_response(activity_id=1)
        self.assertEqual(response.status_code, 404)

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_redirect_on_base_invalidness(self, mock_tz):
        # Sign-ups are not open, so one can not create a slot
        response = self.build_get_response(iso_dt='2020-08-26T14:00:00+00:00', follow=True)
        # self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('activity_calendar:activity_slots_on_day', kwargs={
            'activity_id': 2,
            'recurrence_id': datetime.datetime.fromisoformat('2020-08-26T14:00:00+00:00'),
        }))
        self.assertHasMessage(response, level=messages.ERROR, text="closed")

        # Slots are created automatically on this activity, so can't be created by hand
        response = self.build_get_response(iso_dt='2020-08-14T19:00:00+00:00', follow=True, activity_id=1)
        self.assertRedirects(response, reverse('activity_calendar:activity_slots_on_day', kwargs={
            'activity_id': 1,
            'recurrence_id': datetime.datetime.fromisoformat('2020-08-14T19:00:00+00:00'),
        }))
        self.assertHasMessage(response, level=messages.ERROR, text="can not create slots on this activity")

        # Assume that it will do the same in all other cases

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_normal_get_page(self, mock_tz):
        # The basic set-up is valid. User can create a slot
        response = self.build_get_response()
        self.assertEqual(response.status_code, 200)

        # Test standard context attributes
        self.assertIn('activity', response.context)
        self.assertIn('form', response.context)
        self.assertIn('recurrence_id', response.context)
        self.assertIn('subscriptions_open', response.context)
        self.assertIn('num_total_participants', response.context)
        self.assertIn('num_max_participants', response.context)
        self.assertIn('user_subscriptions', response.context)
        self.assertIn('subscribed_slots', response.context)

    def test_error_codes(self):
        """ Test that the error code messages in the view are present. Used when defaulting base view for some reason """
        self.assertIn('activity-full', CreateSlotView.error_messages)
        self.assertIn('invalid', CreateSlotView.error_messages)
        self.assertIn('closed', CreateSlotView.error_messages)
        self.assertIn('max-slots-occupied', CreateSlotView.error_messages)
        self.assertIn('max-slots-claimed', CreateSlotView.error_messages)
        self.assertIn('user-slot-creation-denied', CreateSlotView.error_messages)

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_unsuccesfull_post(self, mock_tz):
        # An empty response is bound to create some form of error in the form
        response = self.build_post_response({
        }, follow=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())

        self.assertHasMessage(response, level=messages.ERROR, text="correct your data")

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_successful_post(self, mock_tz):
        response = self.build_post_response({
            'sign_up': True,
            'title': "Test slot",
            'max_participants': 4,
        }, follow=True)

        self.assertRedirects(response, reverse('activity_calendar:activity_slots_on_day', kwargs={
            'activity_id': 2,
            'recurrence_id': datetime.datetime.fromisoformat('2020-08-12T14:00:00+00:00'),
        }))
        self.assertTrue(ActivitySlot.objects.filter().exists())
        msg = _("You have successfully created and joined '{activity_name}'").format(activity_name="Test slot")
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)

        # Test the message presented when not joining the slot
        response = self.build_post_response({
            'sign_up': False,
            'title': "Test slot",
            'max_participants': 4,
        }, follow=True)
        self.assertTrue(ActivitySlot.objects.filter().exists())
        msg = _("You have successfully created '{activity_name}'").format(activity_name="Test slot")
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_creation_none_denied(self, mock_tz):
        Activity.objects.filter(id=2).update(slot_creation=Activity.SLOT_CREATION_STAFF)
        response = self.client.get(self.base_url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('activity_calendar:activity_slots_on_day', kwargs={
            'activity_id': 2,
            'recurrence_id': datetime.datetime.fromisoformat('2020-08-12T14:00:00+00:00'),
        }))
        msg = str(_("You can not create slots on this activity."))  # add str() to run the proxy
        self.assertHasMessage(response, level=messages.ERROR, text=msg)

    @patch('django.utils.timezone.now', side_effect=mock_now())
    def test_creation_none_valid_for_admin(self, mock_tz):
        # Set current user is superuser
        self.client.force_login(User.objects.get(is_superuser=True))

        Activity.objects.filter(id=2).update(slot_creation=Activity.SLOT_CREATION_STAFF)
        response = self.client.get(self.base_url, follow=False)
        self.assertEqual(response.status_code, 200)


class EditActivityMomentDataView(TestActivityViewMixin, TestCase):
    default_url_name = "edit_moment"
    default_activity_id = 2
    default_iso_dt = '2020-08-26T14:00:00+00:00'

    def test_normal_get_page(self):
        # The basic set-up is valid. User can create a slot
        # Login a superuser so it always has the required permission
        user = User.objects.get(is_superuser=True)
        self.client.force_login(user)

        response = self.build_get_response()
        self.assertEqual(response.status_code, 200)

        # Test standard context attributes
        self.assertIn('activity', response.context)
        self.assertIn('form', response.context)
        self.assertIn('recurrence_id', response.context)
        self.assertIn('activity_moment', response.context)

        self.assertIsNotNone(response.context['form'])
        self.assertIsInstance(response.context['form'], ActivityMomentForm)

        # User must've been passed to the form (for MarkdownImage uploads)
        self.assertEqual(response.context['form'].user, user)

    def test_requires_permission(self):
        self.assertTrue(issubclass(EditActivityMomentView, PermissionRequiredMixin))
        self.assertIn('activity_calendar.change_activitymoment', EditActivityMomentView.permission_required)

    def test_successful_post(self):
        """ Tests that a successful post is processed correctly """
        self.client.force_login(User.objects.get(is_superuser=True))

        new_title = "A_new_title_test"

        response = self.build_post_response({'local_title': new_title,}, follow=True)

        # Assert redirect after success
        self.assertRedirects(response, reverse('activity_calendar:activity_slots_on_day', kwargs={
            'activity_id': self.default_activity_id,
            'recurrence_id': datetime.datetime.fromisoformat(self.default_iso_dt),
        }))
        msg = _("You have successfully changed the settings for '{activity_name}'").format(activity_name=new_title)
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)

        # Assert that the instance is saved
        self.assertIsNotNone(ActivityMoment.objects.filter(local_title=new_title,).first())
