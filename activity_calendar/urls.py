from django.conf import settings
from django.urls import path, include, register_converter, reverse_lazy
from django.views.generic.base import RedirectView

from . import views, api
from .feeds import PublicCalendarFeed, CustomCalendarFeed

from activity_calendar.url_converters import DateTimeIsoConverter

register_converter(DateTimeIsoConverter, 'dt')

urlpatterns = [

    path('activities/', include([
        path('', views.ActivityOverview.as_view(), name='activity_upcoming'),
        path('calendar/', views.activity_collection, name='calendar'),
        path('activity/<int:activity_id>/<dt:recurrence_id>/', include([
            path('', views.get_activity_detail_view, name='activity_slots_on_day'),
            path('create_slot/', views.CreateSlotView.as_view(), name='create_slot'),
            path('edit/', views.EditActivityMomentView.as_view(), name='edit_moment'),
            path('cancel/', views.CancelActivityMomentView.as_view(), name='cancel_moment'),
        ])),
    ])),

    path('api/calendar/ical', PublicCalendarFeed(), name='icalendar'),
    path('api/calendar/<slug:calendar_slug>/', CustomCalendarFeed(), name='icalendar'),
    path('api/calendar/fullcalendar', api.fullcalendar_feed, name='fullcalendar_feed'),
    path('api/activities/upcoming/', api.upcoming_core_feed, name='upcoming_core_feed'),

    # Some mails contained the old calendar url, redirect them to the new activity page
    path('calendar/', RedirectView.as_view(url=reverse_lazy('activity_calendar:activity_upcoming'))),
]
