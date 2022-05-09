from django.urls import path, include, reverse

from committees.committeecollective import CommitteeBaseConfig

from activity_calendar.committee_pages.views import ActivityCalendarView, AddActivityMomentCalendarView



class ActivityConfig(CommitteeBaseConfig):
    url_keyword = 'activity'
    name = 'Activities'
    icon_class = 'fas fa-calendar'
    url_name = 'group_activities'
    group_requires_permission = 'activity_calendar.view_activity'

    def get_urls(self):
        """ Builds a list of urls """
        return [
            path('', ActivityCalendarView.as_view(config=self), name='group_activities'),
            path('<int:activity_id>/add/', AddActivityMomentCalendarView.as_view(config=self), name='add_activity_moment'),
        ]
