from datetime import datetime
from django.contrib.auth.models import Permission
from django.contrib import messages
from django.test import TestCase
from django.urls import reverse
from django.utils import dateparse
from django.views.generic import ListView, FormView

from activity_calendar.models import Activity, OrganiserLink
from committees.tests.committee_pages.utils import AssocationGroupTestingMixin
from committees.mixins import AssociationGroupMixin
from core.tests.util import suppress_warnings
from utils.testing.view_test_utils import ViewValidityMixin

from activity_calendar.committee_pages.forms import *
from activity_calendar.committee_pages.views import *


class TestCommitteeActivityOverview(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    fixtures = [
        "test_users",
        "test_groups",
        "test_members",
        "committees/associationgroups",
        "test_activity_slots",
        "activity_calendar/test_activity_organisers",
    ]
    base_user_id = 40
    association_group_id = 41
    url_name = "group_activities"

    def test_class(self):
        self.assertTrue(issubclass(ActivityCalendarView, AssociationGroupMixin))
        self.assertTrue(issubclass(ActivityCalendarView, ListView))
        self.assertEqual(
            ActivityCalendarView.template_name, "activity_calendar/committee_pages/committee_activities.html"
        )
        self.assertEqual(ActivityCalendarView.context_object_name, "activities")

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

        # Test context
        self.assertEqual(response.context["activities"].count(), 1)
        self.assertIn(Activity.objects.get(id=2), response.context["activities"])

    def test_archived_in_queryset(self):
        """Tests that the archived setting excludes an activity from the activity list"""
        OrganiserLink.objects.filter(id=42).update(archived=True)
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

        # Test context
        self.assertEqual(response.context["activities"].count(), 0)
        self.assertNotIn(Activity.objects.get(id=2), response.context["activities"])


class TestCommitteeActivityAddActivityMomentView(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    fixtures = [
        "test_users",
        "test_groups",
        "test_members",
        "committees/associationgroups",
        "test_activity_slots",
        "activity_calendar/test_activity_organisers",
    ]
    base_user_id = 40
    association_group_id = 41
    url_name = "add_activity_moment"
    group_permissions_required = "activity_calendar.add_activitymoment"

    def setUp(self):
        super(TestCommitteeActivityAddActivityMomentView, self).setUp()
        self.activity = Activity.objects.get(id=2)

    def get_url_kwargs(self, **kwargs):
        return super(TestCommitteeActivityAddActivityMomentView, self).get_url_kwargs(activity_id=3, **kwargs)

    def test_class(self):
        self.assertTrue(issubclass(AddActivityMomentCalendarView, AssociationGroupMixin))
        self.assertTrue(issubclass(AddActivityMomentCalendarView, FormView))
        self.assertEqual(
            AddActivityMomentCalendarView.template_name,
            "activity_calendar/committee_pages/committee_add_moment_page.html",
        )
        self.assertEqual(AddActivityMomentCalendarView.form_class, CreateActivityMomentForm)

    @suppress_warnings
    def test_add_activitymoment_access(self):
        self.association_group.permissions.remove(Permission.objects.get(codename="add_activitymoment"))

        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 403)

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)


class MeetingOverviewTestCase(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    fixtures = ["activity_calendar/test_meetings"]
    base_user_id = 67
    association_group_id = 60
    url_name = "meetings:home"
    group_permissions_required = ["activity_calendar.can_host_meetings"]

    def test_class(self):
        self.assertTrue(issubclass(MeetingOverview, AssociationGroupMixin))
        self.assertTrue(issubclass(MeetingOverview, ListView))
        self.assertEqual(MeetingOverview.template_name, "activity_calendar/committee_pages/meeting_home.html")

    def test_successful_get(self):
        self.assertValidGetResponse()


class MeetingRecurrenceFormViewTestCase(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    fixtures = ["activity_calendar/test_meetings"]
    base_user_id = 67
    association_group_id = 60
    url_name = "meetings:edit_recurrence"
    group_permissions_required = [
        "activity_calendar.can_host_meetings",
        "activity_calendar.change_meeting_recurrences",
    ]
    recurrence_id = "2023-03-25T19:00:00Z"

    def test_class(self):
        self.assertTrue(issubclass(MeetingRecurrenceFormView, AssociationGroupMixin))
        self.assertTrue(issubclass(MeetingRecurrenceFormView, FormView))
        self.assertEqual(
            MeetingRecurrenceFormView.template_name, "activity_calendar/committee_pages/meeting_recurrences.html"
        )
        self.assertEqual(MeetingRecurrenceFormView.form_class, MeetingRecurrenceForm)

    def test_successful_get(self):
        self.assertValidGetResponse()

    def test_succesful_post(self):
        data = {"start_date": "2023-03-01T12:30:00Z", "recurrences": "RRULE:FREQ=WEEKLY;UNTIL=20230330T220000Z"}
        redirect_url = reverse("committees:meetings:home", kwargs={"group_id": self.association_group.id})
        self.assertValidPostResponse(data=data, redirect_url=redirect_url, fetch_redirect_response=False)
        response = self.assertValidGetResponse(url=redirect_url)

        self.assertHasMessage(response, level=messages.SUCCESS)


class AddMeetingViewTestCase(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    fixtures = ["activity_calendar/test_meetings"]
    base_user_id = 67
    association_group_id = 60
    url_name = "meetings:add"
    group_permissions_required = ["activity_calendar.can_host_meetings"]

    def test_class(self):
        self.assertTrue(issubclass(AddMeetingView, AssociationGroupMixin))
        self.assertTrue(issubclass(AddMeetingView, FormView))
        self.assertEqual(AddMeetingView.template_name, "activity_calendar/committee_pages/meeting_add.html")
        self.assertEqual(AddMeetingView.form_class, AddMeetingForm)

    def test_successful_get(self):
        self.assertValidGetResponse()

    def test_succesful_post(self):
        data = {"local_start_date": "2023-03-01T12:00:00Z"}
        redirect_url = reverse("committees:meetings:home", kwargs={"group_id": self.association_group.id})
        self.assertValidPostResponse(data=data, redirect_url=redirect_url, fetch_redirect_response=False)
        response = self.assertValidGetResponse(url=redirect_url)

        self.assertHasMessage(response, level=messages.SUCCESS)


class EditMeetingViewTestCase(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    fixtures = ["activity_calendar/test_meetings"]
    base_user_id = 67
    association_group_id = 60
    url_name = "meetings:edit"
    group_permissions_required = ["activity_calendar.can_host_meetings"]
    recurrence_id = "2023-03-09T19:00:00+00:00"

    def get_url_kwargs(self, recurrence_id=None, **kwargs):
        recurrence_id = recurrence_id or self.recurrence_id

        return super(EditMeetingViewTestCase, self).get_url_kwargs(
            recurrence_id=datetime.fromisoformat(recurrence_id), **kwargs
        )

    @suppress_warnings
    def test_404_on_nonexisting_meeting(self):
        response = self.client.get(self.get_base_url(recurrence_id="2023-03-05T13:13:00+00:00"))
        self.assertEqual(response.status_code, 404)

    def test_class(self):
        self.assertTrue(issubclass(EditMeetingView, AssociationGroupMixin))
        self.assertTrue(issubclass(EditMeetingView, FormView))
        self.assertEqual(EditMeetingView.template_name, "activity_calendar/committee_pages/meeting_edit.html")
        self.assertEqual(EditMeetingView.form_class, EditMeetingForm)

    def test_successful_get(self):
        self.assertValidGetResponse()

    def test_redirect_cancelled_meetings(self):
        recurrence_id = "2023-03-25T19:00:00+00:00"
        response = self.client.get(self.get_base_url(recurrence_id=recurrence_id), follow=False)
        redirect_url = reverse(
            "committees:meetings:un-cancel",
            kwargs={
                "group_id": self.association_group.id,
                "recurrence_id": datetime.fromisoformat(recurrence_id),
            },
        )
        self.assertRedirects(response, expected_url=redirect_url, fetch_redirect_response=False)

    def test_succesful_post(self):
        data = {}
        redirect_url = reverse("committees:meetings:home", kwargs={"group_id": self.association_group.id})
        self.assertValidPostResponse(data=data, redirect_url=redirect_url, fetch_redirect_response=False)
        response = self.assertValidGetResponse(url=redirect_url)

        self.assertHasMessage(response, level=messages.SUCCESS)


class EditCancelledMeetingViewTestCase(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    fixtures = ["activity_calendar/test_meetings"]
    base_user_id = 67
    association_group_id = 60
    url_name = "meetings:un-cancel"
    group_permissions_required = ["activity_calendar.can_host_meetings"]
    recurrence_id = "2023-03-25T19:00:00+00:00"

    def get_url_kwargs(self, recurrence_id=None, **kwargs):
        recurrence_id = recurrence_id or self.recurrence_id

        return super(EditCancelledMeetingViewTestCase, self).get_url_kwargs(
            recurrence_id=datetime.fromisoformat(recurrence_id), **kwargs
        )

    def test_class(self):
        self.assertTrue(issubclass(EditCancelledMeetingView, AssociationGroupMixin))
        self.assertTrue(issubclass(EditCancelledMeetingView, FormView))
        self.assertEqual(
            EditCancelledMeetingView.template_name, "activity_calendar/committee_pages/meeting_edit_cancelled.html"
        )
        self.assertEqual(EditCancelledMeetingView.form_class, EditCancelledMeetingForm)

    @suppress_warnings
    def test_404_on_nonexisting_meeting(self):
        response = self.client.get(self.get_base_url(recurrence_id="2023-03-05T13:13:00+00:00"))
        self.assertEqual(response.status_code, 404)

    def test_successful_get(self):
        self.assertValidGetResponse()

    def test_redirect_non_cancelled_meetings(self):
        recurrence_id = "2023-03-09T19:00:00+00:00"
        response = self.client.get(self.get_base_url(recurrence_id=recurrence_id), follow=False)
        redirect_url = reverse(
            "committees:meetings:edit",
            kwargs={
                "group_id": self.association_group.id,
                "recurrence_id": datetime.fromisoformat(recurrence_id),
            },
        )
        self.assertRedirects(response, expected_url=redirect_url, fetch_redirect_response=False)

    def test_succesful_post(self):
        data = {}
        redirect_url = reverse(
            "committees:meetings:edit",
            kwargs={
                "group_id": self.association_group.id,
                "recurrence_id": dateparse.parse_datetime(self.recurrence_id),
            },
        )
        self.assertValidPostResponse(data=data, redirect_url=redirect_url, fetch_redirect_response=False)
        response = self.assertValidGetResponse(url=redirect_url)

        self.assertHasMessage(response, level=messages.SUCCESS)


class DeleteMeetingViewTestCase(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    fixtures = ["activity_calendar/test_meetings"]
    base_user_id = 67
    association_group_id = 60
    url_name = "meetings:delete"
    group_permissions_required = ["activity_calendar.can_host_meetings"]
    recurrence_id = "2023-03-09T19:00:00+00:00"

    def get_url_kwargs(self, recurrence_id=None, **kwargs):
        recurrence_id = recurrence_id or self.recurrence_id

        return super(DeleteMeetingViewTestCase, self).get_url_kwargs(
            recurrence_id=datetime.fromisoformat(recurrence_id), **kwargs
        )

    def test_class(self):
        self.assertTrue(issubclass(DeleteMeetingView, AssociationGroupMixin))
        self.assertTrue(issubclass(DeleteMeetingView, FormView))
        self.assertEqual(DeleteMeetingView.template_name, "activity_calendar/committee_pages/meeting_cancel.html")
        self.assertEqual(DeleteMeetingView.form_class, CancelMeetingForm)

    @suppress_warnings
    def test_404_on_nonexisting_meeting(self):
        response = self.client.get(self.get_base_url(recurrence_id="2023-03-05T13:13:00+00:00"))
        self.assertEqual(response.status_code, 404)

    def test_successful_get(self):
        self.assertValidGetResponse()

    def test_catch_already_cancelled_meetings(self):
        recurrence_id = "2023-03-25T19:00:00+00:00"
        response = self.client.get(self.get_base_url(recurrence_id=recurrence_id), follow=False)
        redirect_url = reverse("committees:meetings:home", kwargs={"group_id": self.association_group.id})
        self.assertRedirects(response, expected_url=redirect_url, fetch_redirect_response=False)
        response = self.client.get(redirect_url)
        self.assertHasMessage(response, level=messages.ERROR)

    def test_succesful_post(self):
        data = {}
        redirect_url = reverse("committees:meetings:home", kwargs={"group_id": self.association_group.id})
        self.assertValidPostResponse(data=data, redirect_url=redirect_url, fetch_redirect_response=False)
        response = self.assertValidGetResponse(url=redirect_url)

        self.assertHasMessage(response, level=messages.SUCCESS)
