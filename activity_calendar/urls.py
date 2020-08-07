from django.urls import path
from . import views
from .feeds import EventFeed

urlpatterns = [
    path('', views.activity_collection, name='activity_collection'),
    path('googlehtml/', views.activity_collection, name='googlehtml_activity_collection'),
    path('ical/', EventFeed(), name='icalendar'),
    path('fullcalendar/', views.fullcalendar_feed, name='fullcalendar_feed')
]
