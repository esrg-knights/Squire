from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.views.generic import ListView, UpdateView

from activity_calendar.models import Activity
from utils.views import SearchFormMixin


from committees.views import AssociationGroupMixin



class ActivityCalendarView(AssociationGroupMixin, ListView):
    template_name = "activity_calendar/committee_pages/committee_activities.html"
    context_object_name = 'activities'

    def get_queryset(self):
        return Activity.objects.filter(organiserlink__association_group=self.association_group)

    def get_context_data(self, **kwargs):
        # Set a list of availlable content types
        # Used for url creation to add-item pages

        context = super(ActivityCalendarView, self).get_context_data(
            tab_selected='tab_activity',
            **kwargs,
        )

        return context
