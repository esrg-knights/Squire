import datetime

from django.test import TestCase, Client
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from unittest.mock import patch

from activity_calendar.models import *
from activity_calendar.views import CreateSlotView, ActivityMomentWithSlotsView, ActivitySimpleMomentView,\
    EditActivityMomentView
from activity_calendar.forms import *

from core.models import ExtendedUser as User
from core.util import suppress_warnings

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

        self.assertEqual(context['num_total_participants'], 2)

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
        self.assertIn('participants', response.context)
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
        slot.participants.add(self.user)

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
    def test_normal_get_page_signed_up(self, mock_tz):
        # Add the user
        slot = ActivitySlot.objects.filter(
            parent_activity_id=self.default_activity_id,
            recurrence_id=self.recurrence_id,
        ).first()
        slot.participants.add(self.user)

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
        # Can not unsubscribe from an activity you are not regitered to.
        response = self.build_post_response({
            'sign_up': True,
            'slot_id': 8
        }, follow=True)

        self.assertRedirects(response, self.base_url) # Should redirect to prevent resending the post on page refresh
        self.assertTrue(ActivitySlot.objects.filter().exists())
        self.assertHasMessage(response,
                              level=messages.ERROR,
                              text=ActivityMomentWithSlotsView.error_messages['slot-full'])


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
        self.client.force_login(User.objects.get(is_superuser=True))

        response = self.build_get_response()
        self.assertEqual(response.status_code, 200)

        # Test standard context attributes
        self.assertIn('activity', response.context)
        self.assertIn('form', response.context)
        self.assertIn('recurrence_id', response.context)
        self.assertIn('activity_moment', response.context)

        self.assertIsInstance(response.context['form'], ActivityMomentForm)

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



