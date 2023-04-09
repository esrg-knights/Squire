from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import ListView, FormView
from django.shortcuts import get_object_or_404
from django.utils import timezone

from committees.mixins import AssociationGroupMixin, AssociationGroupPermissionRequiredMixin

from activity_calendar.committee_pages.forms import (
    CreateActivityMomentForm,
    AddMeetingForm,
    EditMeetingForm,
    MeetingRecurrenceForm,
    CancelMeetingForm,
    EditCancelledMeetingForm,
)
from activity_calendar.committee_pages.utils import get_meeting_activity
from activity_calendar.constants import ActivityType
from activity_calendar.models import Activity, ActivityMoment
from activity_calendar.templatetags.activity_tags import get_next_activity_instances

__all__ = [
    "ActivityCalendarView",
    "AddActivityMomentCalendarView",
    "MeetingOverview",
    "MeetingRecurrenceFormView",
    "AddMeetingView",
    "EditMeetingView",
    "EditCancelledMeetingView",
    "DeleteMeetingView",
]


class ActivityCalendarView(AssociationGroupMixin, ListView):
    template_name = "activity_calendar/committee_pages/committee_activities.html"
    context_object_name = "activities"

    def get_queryset(self):
        return Activity.objects.filter(
            organiserlink__archived=False,
            organiserlink__association_group=self.association_group,
        ).exclude(type=ActivityType.ACTIVITY_MEETING)

    def get_context_data(self, **kwargs):
        # Set a list of availlable content types
        # Used for url creation to add-item pages

        context = super(ActivityCalendarView, self).get_context_data(
            can_add_activitymoments=self.association_group.has_perm("activity_calendar.add_activitymoment"),
            **kwargs,
        )

        return context


class AddActivityMomentCalendarView(AssociationGroupMixin, FormView):
    form_class = CreateActivityMomentForm
    template_name = "activity_calendar/committee_pages/committee_add_moment_page.html"

    def setup(self, request, *args, **kwargs):
        super(AddActivityMomentCalendarView, self).setup(request, *args, **kwargs)
        # Django calls the following line only in get(), which is too late
        self.activity = get_object_or_404(Activity, id=self.kwargs.get("activity_id"))

        if not self.association_group.has_perm("activity_calendar.add_activitymoment"):
            raise PermissionDenied()

    def get_form_kwargs(self):
        kwargs = super(AddActivityMomentCalendarView, self).get_form_kwargs()
        kwargs["activity"] = self.activity

        return kwargs

    def get_context_data(self, **kwargs):
        return super(AddActivityMomentCalendarView, self).get_context_data(activity=self.activity, **kwargs)

    def form_valid(self, form):
        self.form = form
        self.form.save()
        return super(AddActivityMomentCalendarView, self).form_valid(form)

    def get_success_url(self):
        return self.form.instance.get_absolute_url()


class MeetingOverview(AssociationGroupMixin, ListView):
    template_name = "activity_calendar/committee_pages/meeting_home.html"
    context_object_name = "meeting_list"

    def get_queryset(self):
        start_dt = timezone.now() - timedelta(hours=2)
        activity = get_meeting_activity(association_group=self.association_group)
        return get_next_activity_instances(activity, start_dt=start_dt, max=5)

    def get_context_data(self, **kwargs):
        return super(MeetingOverview, self).get_context_data(
            meeting_activity=get_meeting_activity(self.association_group),
            can_change_recurrences=self.association_group.has_perm("activity_calendar.change_meeting_recurrences"),
            feed_url=reverse("activity_calendar:meetings_feed", kwargs={"group_id": self.association_group.id}),
            **kwargs,
        )


class MeetingRecurrenceFormView(AssociationGroupMixin, AssociationGroupPermissionRequiredMixin, FormView):
    group_permissions_required = "activity_calendar.change_meeting_recurrences"
    form_class = MeetingRecurrenceForm
    template_name = "activity_calendar/committee_pages/meeting_recurrences.html"

    def setup(self, request, *args, **kwargs):
        super(MeetingRecurrenceFormView, self).setup(request, *args, **kwargs)
        self.meeting_activity = get_meeting_activity(self.association_group)

    def get_form_kwargs(self):
        kwargs = super(MeetingRecurrenceFormView, self).get_form_kwargs()
        kwargs["instance"] = self.meeting_activity
        return kwargs

    def form_valid(self, form):
        form.save()
        msg = f"Recurrences have been adjusted"
        messages.success(self.request, msg)
        return super(MeetingRecurrenceFormView, self).form_valid(form)

    def get_success_url(self):
        return reverse("committees:meetings:home", kwargs={"group_id": self.association_group.id})


class AddMeetingView(AssociationGroupMixin, FormView):
    form_class = AddMeetingForm
    template_name = "activity_calendar/committee_pages/meeting_add.html"

    def get_form_kwargs(self):
        kwargs = super(AddMeetingView, self).get_form_kwargs()
        kwargs["association_group"] = self.association_group
        return kwargs

    def form_valid(self, form):
        form.save()
        meeting_time = form.instance.local_start_date
        msg = f"A new meeting has been added on {meeting_time.strftime('%B %d')} at {meeting_time.strftime('%H:%M')}"
        messages.success(self.request, msg)
        return super(AddMeetingView, self).form_valid(form)

    def get_success_url(self):
        return reverse("committees:meetings:home", kwargs={"group_id": self.association_group.id})


class MeetingMixin:
    """Mixin for meeting views"""

    def setup(self, request, *args, **kwargs):
        super(MeetingMixin, self).setup(request, *args, **kwargs)

        activity = get_meeting_activity(self.association_group)
        self.activity_moment = activity.get_occurrence_at(self.kwargs["recurrence_id"])
        if self.activity_moment is None:
            raise Http404("There is no meeting at this occurence")

    def get_context_data(self, **kwargs):
        return super(MeetingMixin, self).get_context_data(meeting=self.activity_moment, **kwargs)


class EditMeetingView(AssociationGroupMixin, MeetingMixin, FormView):
    form_class = EditMeetingForm
    template_name = "activity_calendar/committee_pages/meeting_edit.html"

    def dispatch(self, request, *args, **kwargs):
        if self.activity_moment.is_cancelled:
            return HttpResponseRedirect(
                redirect_to=reverse(
                    "committees:meetings:un-cancel",
                    kwargs={
                        "group_id": self.association_group.id,
                        "recurrence_id": self.activity_moment.recurrence_id,
                    },
                )
            )
        return super(EditMeetingView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(EditMeetingView, self).get_form_kwargs()
        kwargs["instance"] = self.activity_moment
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Meeting has succesfully been adjusted")
        return super(EditMeetingView, self).form_valid(form)

    def get_success_url(self):
        return reverse("committees:meetings:home", kwargs={"group_id": self.association_group.id})


class EditCancelledMeetingView(AssociationGroupMixin, MeetingMixin, FormView):
    form_class = EditCancelledMeetingForm
    template_name = "activity_calendar/committee_pages/meeting_edit_cancelled.html"

    def dispatch(self, request, *args, **kwargs):
        if not self.activity_moment.is_cancelled:
            return HttpResponseRedirect(redirect_to=self.get_success_url())
        return super(EditCancelledMeetingView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(EditCancelledMeetingView, self).get_form_kwargs()
        kwargs["instance"] = self.activity_moment
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Meeting has been un-cancelled and can now be edited")
        return super(EditCancelledMeetingView, self).form_valid(form)

    def get_success_url(self):
        return reverse(
            "committees:meetings:edit",
            kwargs={
                "group_id": self.association_group.id,
                "recurrence_id": self.activity_moment.recurrence_id,
            },
        )


class DeleteMeetingView(AssociationGroupMixin, MeetingMixin, FormView):
    form_class = CancelMeetingForm
    template_name = "activity_calendar/committee_pages/meeting_cancel.html"

    def dispatch(self, request, *args, **kwargs):
        if self.activity_moment.is_cancelled:
            message = "This meeting was already cancelled"
            messages.error(request, message)
            return HttpResponseRedirect(redirect_to=self.get_success_url())
        return super(DeleteMeetingView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(DeleteMeetingView, self).get_form_kwargs()
        kwargs["instance"] = self.activity_moment
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Meeting has is now marked as cancelled")
        return super(DeleteMeetingView, self).form_valid(form)

    def get_success_url(self):
        return reverse("committees:meetings:home", kwargs={"group_id": self.association_group.id})
