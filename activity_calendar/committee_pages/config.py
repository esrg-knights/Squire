from django.urls import path, include, reverse, register_converter

from committees.committeecollective import CommitteeBaseConfig

from activity_calendar.committee_pages import views
from activity_calendar.url_converters import DateTimeIsoConverter
from activity_calendar.committee_pages.options import MessageOptions

register_converter(DateTimeIsoConverter, "dt")


class ActivityConfig(CommitteeBaseConfig):
    url_keyword = "activity"
    name = "Activities"
    icon_class = "fas fa-calendar"
    url_name = "group_activities"
    group_requires_permission = "activity_calendar.view_activity"

    def get_urls(self):
        """Builds a list of urls"""
        return [
            path("", views.ActivityCalendarView.as_view(config=self), name="group_activities"),
            path(
                "<int:activity_id>/add/",
                views.AddActivityMomentCalendarView.as_view(config=self),
                name="add_activity_moment",
            ),
        ]


class MeetingConfig(CommitteeBaseConfig):
    url_keyword = "meetings"
    name = "Meetings"
    icon_class = "fas fa-scroll"
    url_name = "meetings:home"
    group_requires_permission = "activity_calendar.can_host_meetings"
    namespace = "meetings"
    setting_option_classes = [MessageOptions]

    def get_urls(self):
        """Builds a list of urls"""
        return [
            path("", views.MeetingOverview.as_view(config=self), name="home"),
            path("add/", views.AddMeetingView.as_view(config=self), name="add"),
            path("edit-recurrence/", views.MeetingRecurrenceFormView.as_view(config=self), name="edit_recurrence"),
            path(
                "<dt:recurrence_id>/",
                include(
                    [
                        path("edit/", views.EditMeetingView.as_view(config=self), name="edit"),
                        path("activate/", views.EditCancelledMeetingView.as_view(config=self), name="un-cancel"),
                        path("delete/", views.DeleteMeetingView.as_view(config=self), name="delete"),
                    ]
                ),
            ),
        ]
