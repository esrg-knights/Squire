from django.urls import path
from . import views
from .models import EventFeed

urlpatterns = [
    path('', views.activity_collection, name='activity_collection'),
    path('ical/', EventFeed(), name='icalendar'),
]
