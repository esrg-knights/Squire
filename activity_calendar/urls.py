from django.urls import path, include
from . import views, api
from .feeds import CESTEventFeed

urlpatterns = [

    path('calendar/', include([
        path('', views.activity_collection, name='calendar'),
        path('google_html', views.googlehtml_activity_collection, name='googlehtml_activity_collection'),
        path('activity/', include([
            path('<int:activity_id>/', views.ActivitySlotList.as_view(), name='activity_slots_on_day'),
            path('slot/<int:slot_id>/', include([
                path('register', views.RegisterToSlotView.as_view(), name='activity_register'),
            ])),
        ])),
    ])),

    path('api/calendar/ical', CESTEventFeed(), name='icalendar'),
    path('api/calendar/fullcalendar', api.fullcalendar_feed, name='fullcalendar_feed'),
    # path('api/calendar/register/<int:slot_id>', api.register, name='activity_register'),
    path('api/calendar/deregister/<int:slot_id>', api.deregister, name='activity_deregister'),
]
