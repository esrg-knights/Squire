
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.models import Permission
from django.test import TestCase, Client
from django.urls import reverse
from django.views.generic import ListView, FormView

from activity_calendar.models import Activity
from committees.models import AssociationGroup
from committees.views import AssociationGroupMixin
from core.tests.util import suppress_warnings
from utils.testing.view_test_utils import ViewValidityMixin, TestMixinMixin

from activity_calendar.committee_pages.forms import CreateActivityMomentForm
from activity_calendar.committee_pages.views import ActivityCalendarView, AddActivityMomentCalendarView



class AssocationGroupTestingMixin:
    association_group_id = None
    association_group = None
    url_name = None

    def setUp(self):
        super(AssocationGroupTestingMixin, self).setUp()
        if self.association_group_id is None:
            raise ImproperlyConfigured(f"'association_group_id' was not defined on {self.__class__.__name__}")
        self.association_group = AssociationGroup.objects.get(id=self.association_group_id)

    def get_base_url(self):
        if self.url_name is None:
            raise ImproperlyConfigured(f"'url_name' was not defined on {self.__class__.__name__}")
        return reverse('committees:'+self.url_name, kwargs=self.get_url_kwargs())

    def get_url_kwargs(self, **kwargs):
        url_kwargs = {
            'group_id': self.association_group_id,
        }
        url_kwargs.update(kwargs)
        return url_kwargs


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

