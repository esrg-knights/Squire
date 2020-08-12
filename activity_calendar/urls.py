from django.urls import path
from . import views
from .feeds import CESTEventFeed

urlpatterns = [
    path('calendar/google_html', views.googlehtml_activity_collection, name='googlehtml_activity_collection'),
    path('calendar', views.activity_collection, name='activity_collection'),
    path('api/calendar/ical', CESTEventFeed(), name='icalendar'),
    path('api/calendar/activities', views.fullcalendar_feed, name='fullcalendar_feed')
]
