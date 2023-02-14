from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import reverse
from django.views.generic import ListView, FormView
from django.shortcuts import get_object_or_404

from committees.committeecollective import AssociationGroupMixin
from utils.auth_utils import get_perm_from_name

from activity_calendar.models import Activity, ActivityMoment
from activity_calendar.committee_pages.forms import CreateActivityMomentForm, AddMeetingForm, \
    EditMeetingForm, MeetingRecurrenceForm, DeleteMeetingForm
from activity_calendar.templatetags.activity_tags import get_next_activity_instances
from activity_calendar.committee_pages.utils import get_meeting_activity

__all__ = ["ActivityCalendarView", "AddActivityMomentCalendarView", "MeetingOverview"]

class ActivityCalendarView(AssociationGroupMixin, ListView):
    template_name = "activity_calendar/committee_pages/committee_activities.html"
    context_object_name = 'activities'

    def get_queryset(self):
        return Activity.objects.filter(
            organiserlink__archived=False,
            organiserlink__association_group=self.association_group
        )

    def get_context_data(self, **kwargs):
        # Set a list of availlable content types
        # Used for url creation to add-item pages

        context = super(ActivityCalendarView, self).get_context_data(
            can_add_activitymoments=self.association_group.site_group.permissions.
                                        filter(codename="add_activitymoment").exists(),
            **kwargs,
        )

        return context

class AddActivityMomentCalendarView(AssociationGroupMixin, FormView):
    form_class = CreateActivityMomentForm
    template_name = "activity_calendar/committee_pages/committee_add_moment_page.html"

    def setup(self, request, *args, **kwargs):
        super(AddActivityMomentCalendarView, self).setup(request, *args, **kwargs)
        # Django calls the following line only in get(), which is too late
        self.activity = get_object_or_404(Activity, id=self.kwargs.get('activity_id'))

        if not self.association_group.site_group.permissions.filter(codename="add_activitymoment").exists():
            raise PermissionDenied()

    def get_form_kwargs(self):
        kwargs = super(AddActivityMomentCalendarView, self).get_form_kwargs()
        kwargs['activity'] = self.activity

        return kwargs

    def get_context_data(self, **kwargs):
        return super(AddActivityMomentCalendarView, self).get_context_data(
            activity=self.activity,
            **kwargs
        )

    def form_valid(self, form):
        self.form = form
        self.form.save()
        return super(AddActivityMomentCalendarView, self).form_valid(form)

    def get_success_url(self):
        return self.form.instance.get_absolute_url()


class MeetingOverview(AssociationGroupMixin, ListView):
    template_name = "activity_calendar/committee_pages/meetings_home.html"
    context_object_name = "meeting_list"

    def get_queryset(self):
        activity = get_meeting_activity(association_group=self.association_group)
        return get_next_activity_instances(activity, max=8)

    def get_context_data(self, **kwargs):
        can_change_recurrences = get_perm_from_name('activity_calendar.change_meeting_recurrences').\
            group_set.filter(associationgroup=self.association_group).exists()

        return super(MeetingOverview, self).get_context_data(
            meeting_activity=get_meeting_activity(self.association_group),
            can_change_recurrences = can_change_recurrences,
            **kwargs
        )


class MeetingRecurrenceFormView(AssociationGroupMixin, FormView):
    # Todo, filter association_permission = 'change_meeting_recurrences'
    form_class = MeetingRecurrenceForm
    template_name = "activity_calendar/committee_pages/meeting_recurrences.html"

    def setup(self, request, *args, **kwargs):
        super(MeetingRecurrenceFormView, self).setup(request, *args, **kwargs)
        self.meeting_activity = get_meeting_activity(self.association_group)

    def get_form_kwargs(self):
        kwargs = super(MeetingRecurrenceFormView, self).get_form_kwargs()
        kwargs['instance'] = self.meeting_activity
        return kwargs

    def form_valid(self, form):
        form.save()
        msg = f"Recurrences have been adjusted"
        messages.success(self.request, msg)
        return super(MeetingRecurrenceFormView, self).form_valid(form)

    def get_success_url(self):
        return reverse("committees:meetings:home", kwargs={'group_id': self.association_group.id})


class AddMeetingView(AssociationGroupMixin, FormView):
    form_class = AddMeetingForm
    template_name = "activity_calendar/committee_pages/meeting_add.html"

    def get_form_kwargs(self):
        kwargs = super(AddMeetingView, self).get_form_kwargs()
        kwargs['association_group'] = self.association_group
        return kwargs

    def form_valid(self, form):
        form.save()
        msg = f"A new meeting has been added on {form.instance.local_start_date}"
        messages.success(self.request, msg)
        return super(AddMeetingView, self).form_valid(form)

    def get_success_url(self):
        return reverse("committees:meetings:home", kwargs={'group_id': self.association_group.id})


class MeetingMixin:
    """ Mixin for meeting views """
    def setup(self, request, *args, **kwargs):
        super(MeetingMixin, self).setup(request, *args, **kwargs)

        activity = get_meeting_activity(self.association_group)
        self.activity_moment = activity.get_occurrence_at(self.kwargs['recurrence_id'])
        if self.activity_moment is None:
            raise Http404("There is no meeting at this occurence")

    def get_context_data(self, **kwargs):
        return super(MeetingMixin, self).get_context_data(
            meeting=self.activity_moment,
            **kwargs
        )


class EditMeetingView(AssociationGroupMixin, MeetingMixin, FormView):
    form_class = EditMeetingForm
    template_name = "activity_calendar/committee_pages/meeting_edit.html"

    def get_form_kwargs(self):
        kwargs = super(EditMeetingView, self).get_form_kwargs()
        kwargs['instance'] = self.activity_moment
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request,
            "Meeting has succesfully been adjusted"
        )
        return super(EditMeetingView, self).form_valid(form)

    def get_success_url(self):
        return reverse("committees:meetings:home", kwargs={'group_id': self.association_group.id})


class DeleteMeetingView(AssociationGroupMixin, MeetingMixin, FormView):
    form_class = DeleteMeetingForm
    template_name = "activity_calendar/committee_pages/meeting_delete.html"

    def get_form_kwargs(self):
        kwargs = super(DeleteMeetingView, self).get_form_kwargs()
        kwargs['instance'] = self.activity_moment
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request,
            "Meeting has is now marked as cancelled"
        )
        return super(DeleteMeetingView, self).form_valid(form)

    def get_success_url(self):
        return reverse("committees:meetings:home", kwargs={'group_id': self.association_group.id})
