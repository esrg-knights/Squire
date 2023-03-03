from django.test import TestCase

from unittest.mock import patch

from committees.models import AssociationGroup
from utils.testing import FormValidityMixin

from activity_calendar.committee_pages.forms import *
from activity_calendar.constants import *
from activity_calendar.models import ActivityMoment, Activity
from activity_calendar.tests import mock_now
from activity_calendar.widgets import BootstrapDateTimePickerInput


class AddMeetingFormTestCase(FormValidityMixin, TestCase):
    fixtures = ['activity_calendar/test_meetings']
    form_class = AddMeetingForm

    def setUp(self):
        self.association_group = AssociationGroup.objects.get(id=40)
        super(AddMeetingFormTestCase, self).setUp()

    def get_form_kwargs(self, **kwargs):
        kwargs.setdefault('association_group', self.association_group)
        return super(AddMeetingFormTestCase, self).get_form_kwargs(**kwargs)

    def test_start_date_field(self):
        """ Test that the fields contain the minimally defined fields """
        self.assertHasField(
            'local_start_date',
            required=True,
            label='Start date and time',
            widget__class=BootstrapDateTimePickerInput,
        )

    def test_requires_association_group(self):
        """ Assert that a keyerror is raised when the association_group is omitted"""
        with self.assertRaises(KeyError):
            self.form_class(data={}, **super(AddMeetingFormTestCase, self).get_form_kwargs())

    def test_clean_no_conflict_with_activitymoment(self):
        self.assertFormHasError(
            {'local_start_date': "2023-02-24T12:00:00Z"},
            code='already-exists'
        )

    def test_clean_no_conflict_with_recurrent_activity(self):
        self.assertFormHasError(
            {'local_start_date': "2023-03-16T19:00:00Z"},
            code='already-exists'
        )

    def test_save(self):
        form = self.assertFormValid({'local_start_date': "2023-02-27T12:00:00Z"})
        form.save()
        self.assertTrue(ActivityMoment.objects.filter(
            parent_activity__id=40,
            recurrence_id="2023-02-27T12:00:00Z"
        ).exists())


class EditMeetingFormTestCase(FormValidityMixin, TestCase):
    fixtures = ['activity_calendar/test_meetings']
    form_class = EditMeetingForm

    def setUp(self):
        self.activity_moment = ActivityMoment.objects.get(id=41)
        super(EditMeetingFormTestCase, self).setUp()

    def get_form_kwargs(self, **kwargs):
        kwargs.setdefault('instance', self.activity_moment)
        return super(EditMeetingFormTestCase, self).get_form_kwargs(**kwargs)

    def test_has_fields(self):
        """ Test that the fields contain the minimally defined fields """
        self.assertHasField(
            'local_description',
            label='Information'
        )
        self.assertHasField(
            'local_location',
            label='Location'
        )

    def test_form_valid(self):
        self.assertFormValid({})
        self.assertFormValid({
            'local_description': "a new description"
        })
        self.assertFormValid({
            'local_location': "a meeting room"
        })

    def test_save(self):
        self.assertFormValid({
            'local_description': "a new description",
            'local_location': "a meeting room"
        }).save()
        self.activity_moment.refresh_from_db()
        self.assertEqual(
            self.activity_moment.local_description.as_plaintext(),
            "a new description"
        )
        self.assertEqual(
            self.activity_moment.local_location,
            "a meeting room"
        )


class EditCancelledMeetingFormTestCase(FormValidityMixin, TestCase):
    fixtures = ['activity_calendar/test_meetings']
    form_class = EditCancelledMeetingForm

    def setUp(self):
        self.activity_moment = ActivityMoment.objects.get(id=44)
        super(EditCancelledMeetingFormTestCase, self).setUp()

    def get_form_kwargs(self, **kwargs):
        kwargs.setdefault('instance', self.activity_moment)
        return super(EditCancelledMeetingFormTestCase, self).get_form_kwargs(**kwargs)

    def test_fields(self):
        form = self.build_form({})
        self.assertEqual(len(form.fields), 0)

    def test_requires_cancelled(self):
        with self.assertRaises(KeyError):
            self.build_form({}, instance=ActivityMoment.objects.get(id=41))

    def test_save(self):
        self.assertFormValid({}).save()
        self.activity_moment.refresh_from_db()
        self.assertEqual(self.activity_moment.status, STATUS_NORMAL)


class MeetingRecurrenceFormTestCase(FormValidityMixin, TestCase):
    fixtures = ['activity_calendar/test_meetings']
    form_class = MeetingRecurrenceForm

    def setUp(self):
        self.activity = Activity.objects.get(id=40)
        super(MeetingRecurrenceFormTestCase, self).setUp()

    def get_form_kwargs(self, **kwargs):
        kwargs.setdefault('instance', self.activity)
        return super(MeetingRecurrenceFormTestCase, self).get_form_kwargs(**kwargs)

    def test_has_fields(self):
        """ Test that the fields contain the minimally defined fields """
        self.assertHasField('recurrences')
        self.assertHasField('start_date')

    def test_save(self):
        self.assertFormValid({
            'start_date': "2023-03-01T12:30:00Z",
            'recurrences': 'RRULE:FREQ=WEEKLY;UNTIL=20230330T220000Z'
        }).save()
        self.activity.refresh_from_db()
        self.assertEqual(
            self.activity.start_date.__str__(),
            "2023-03-01 12:30:00+00:00"
        )


class CancelMeetingFormTestCase(FormValidityMixin, TestCase):
    fixtures = ['activity_calendar/test_meetings']
    form_class = CancelMeetingForm

    def setUp(self):
        self.activity_moment = ActivityMoment.objects.get(id=41)
        super(CancelMeetingFormTestCase, self).setUp()

    def get_form_kwargs(self, activity_moment_id=None, **kwargs):
        if activity_moment_id:
            kwargs.setdefault('instance', ActivityMoment.objects.get(id=activity_moment_id))
        else:
            kwargs.setdefault('instance', self.activity_moment)
        return super(CancelMeetingFormTestCase, self).get_form_kwargs(**kwargs)

    def test_enable_full_delete_on_additional(self):
        self.assertHasField(
            'full_delete',
            form_kwargs={'activity_moment_id': 43},
            disabled=False,
            help_text="Checking this will delete the meeting entirely",
        )

    def test_disable_full_delete_on_recurrent(self):
        self.assertHasField(
            'full_delete',
            form_kwargs={'activity_moment_id': 41},
            disabled=True,
            help_text='option disabled. Recurrent meetings can not be deleted',
        )

    def test_requires_non_cancelled(self):
        with self.assertRaises(KeyError):
            self.build_form({}, activity_moment_id=44)

    def test_save_cancelled(self):
        form = self.assertFormValid({'full_delete': False}, activity_moment_id=43)
        form.save()
        self.assertEqual(form.instance.status, STATUS_CANCELLED)

    def test_save_delete(self):
        form = self.assertFormValid({'full_delete': True}, activity_moment_id=43)
        form.save()
        self.assertEqual(form.instance.status, STATUS_REMOVED)
