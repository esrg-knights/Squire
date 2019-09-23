"""base URL Configuration
The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    #Change Language helper view
    path('i18n/', include('django.conf.urls.i18n')),
    # Admin Panel
    path('admin/', admin.site.urls),
    # Achievements
    path('achievements/', include('achievements.urls-frontend')),
    path('api/achievements/', include('achievements.urls-api')),
    # Activity Calendar
    path('calendar/', include('activity_calendar.urls-frontend')),
    path('api/calendar/', include('activity_calendar.urls-api')),
    # Membership File
    path('members/', include('membership_file.urls_frontend')),
    path('api/members/', include('membership_file.urls_api')),

    #Redirect all other paths to the core module
    path('', include('core.urls')),
]
