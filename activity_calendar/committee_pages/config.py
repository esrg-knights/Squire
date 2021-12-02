from django.urls import path, include, reverse

from committees.committeecollective import CommitteeConfig

from activity_calendar.committee_pages.views import ActivityCalendarView, AddActivityMomentCalendarView



class ActivityConfig(CommitteeConfig):
    url_keyword = 'activity'
    name = 'Activities'
    url_name = 'group_activities'
    requires_permission = 'activity_calendar.view_activity'

    def get_urls(self):
        """ Builds a list of urls """
        return [
            path('', ActivityCalendarView.as_view(config=self), name='group_activities'),
            path('<int:activity_id>/add/', AddActivityMomentCalendarView.as_view(config=self), name='add_activity_moment'),
        ]
