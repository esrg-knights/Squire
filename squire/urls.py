"""base URL Configuration"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('calendar/', include('activity_calendar.urls')),
    path('achievements/', include('achievements.urls-frontend')),
    path('api/achievements/', include('achievements.urls-api')),
]
