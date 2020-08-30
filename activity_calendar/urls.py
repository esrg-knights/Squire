from django.urls import path
from . import views
from .feeds import CESTEventFeed

urlpatterns = [
    path('calendar/slots/<int:activity_id>', views.ActivitySlotList.as_view(), name='activity_slots_on_day'),
    path('calendar/google_html', views.googlehtml_activity_collection, name='googlehtml_activity_collection'),
    path('calendar', views.activity_collection, name='activity_collection'),
    path('api/calendar/ical', CESTEventFeed(), name='icalendar'),
    path('api/calendar/fullcalendar', views.fullcalendar_feed, name='fullcalendar_feed'),
    path('api/calendar/register/<int:slot_id>', views.register, name='activity_register'),
    path('api/calendar/deregister/<int:slot_id>', views.deregister, name='activity_deregister'),
]
