from django.contrib.auth.models import Permission
from django.test import TestCase
from django.views.generic import ListView, FormView

from activity_calendar.models import Activity, OrganiserLink
from committees.tests.committee_pages.utils import AssocationGroupTestingMixin
from committees.committeecollective import AssociationGroupMixin
from core.tests.util import suppress_warnings
from utils.testing.view_test_utils import ViewValidityMixin

from activity_calendar.committee_pages.forms import CreateActivityMomentForm
from activity_calendar.committee_pages.views import ActivityCalendarView, AddActivityMomentCalendarView


class TestCommitteeActivityOverview(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    fixtures = ['test_users',  'test_groups', 'test_members', 'committees/associationgroups',
                'test_activity_slots', 'activity_calendar/test_activity_organisers']
    base_user_id = 40
    association_group_id = 41
    url_name = 'group_activities'

    def test_class(self):
        self.assertTrue(issubclass(ActivityCalendarView, AssociationGroupMixin))
        self.assertTrue(issubclass(ActivityCalendarView, ListView))
        self.assertEqual(ActivityCalendarView.template_name, "activity_calendar/committee_pages/committee_activities.html")
        self.assertEqual(ActivityCalendarView.context_object_name, 'activities')

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

        # Test context
        self.assertEqual(response.context['activities'].count(), 1)
        self.assertIn(Activity.objects.get(id=2), response.context['activities'])

    def test_archived_in_queryset(self):
        """ Tests that the archived setting excludes an activity from the activity list """
        OrganiserLink.objects.filter(id=42).update(archived=True)
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

        # Test context
        self.assertEqual(response.context['activities'].count(), 0)
        self.assertNotIn(Activity.objects.get(id=2), response.context['activities'])


class TestCommitteeActivityAddActivityMomentView(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    fixtures = ['test_users',  'test_groups', 'test_members', 'committees/associationgroups',
                'test_activity_slots', 'activity_calendar/test_activity_organisers']
    base_user_id = 40
    association_group_id = 41
    url_name = 'add_activity_moment'

    def setUp(self):
        super(TestCommitteeActivityAddActivityMomentView, self).setUp()
        self.activity = Activity.objects.get(id=2)
        self.association_group.site_group.permissions.add(Permission.objects.get(codename='add_activitymoment'))

    def get_url_kwargs(self, **kwargs):
        return super(TestCommitteeActivityAddActivityMomentView, self).get_url_kwargs(
            activity_id=3,
            **kwargs
        )

    def test_class(self):
        self.assertTrue(issubclass(AddActivityMomentCalendarView, AssociationGroupMixin))
        self.assertTrue(issubclass(AddActivityMomentCalendarView, FormView))
        self.assertEqual(AddActivityMomentCalendarView.template_name, "activity_calendar/committee_pages/committee_add_moment_page.html")
        self.assertEqual(AddActivityMomentCalendarView.form_class, CreateActivityMomentForm)

    @suppress_warnings
    def test_add_activitymoment_access(self):
        self.association_group.site_group.permissions.remove(Permission.objects.get(codename='add_activitymoment'))

        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 403)

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

