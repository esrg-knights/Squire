from django.urls import path, include, register_converter
from . import views, api
from .feeds import CESTEventFeed

from activity_calendar.url_converters import DateTimeIsoConverter

register_converter(DateTimeIsoConverter, 'dt')

urlpatterns = [

    path('calendar/', include([
        path('', views.activity_collection, name='calendar'),
        path('google_html', views.googlehtml_activity_collection, name='googlehtml_activity_collection'),
        path('activity/<int:activity_id>/<dt:recurrence_id>/', include([
            path('', views.get_activity_detail_view, name='activity_slots_on_day'),
            path('create_slot/', views.CreateSlotView.as_view(), name='create_slot'),
        ])),
    ])),

    path('api/calendar/ical', CESTEventFeed(), name='icalendar'),
    path('api/calendar/fullcalendar', api.fullcalendar_feed, name='fullcalendar_feed'),
]
