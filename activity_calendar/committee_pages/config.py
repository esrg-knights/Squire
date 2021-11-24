from django.urls import path, include, reverse

from committees.config import CommitteeConfig

from activity_calendar.committee_pages.views import ActivityCalendarView, AddActivityMomentCalendarView



class ActivityConfig(CommitteeConfig):
    url_keyword = 'activity'
    tab_select_keyword = 'tab_activity'
    name = 'Activities'
    url_name = 'committees:group_activities'

    def get_urls(self):
        """ Builds a list of urls """
        return [
            path('', ActivityCalendarView.as_view(config_class=ActivityConfig), name='group_activities'),
            path('<int:activity_id>/add/', AddActivityMomentCalendarView.as_view(config_class=ActivityConfig), name='add_activity_moment'),

        ]
