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

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.conf.urls import handler403, handler404

from committees.urls import get_urls as committee_urls

urlpatterns = [
    #Change Language helper view
    path('i18n/', include('django.conf.urls.i18n')),
    # Admin Panel
    path('admin/', admin.site.urls),
    # Achievements
    path('', include('achievements.urls')),
    # Inventory
    path('inventory/', include(('inventory.urls', 'inventory'), namespace='inventory')),
    path('boardgames/', include(('boardgames.urls', 'boardgames'), namespace='boardgames')),
    path('roleplay/', include(('roleplaying.urls', 'roleplaying'), namespace='roleplaying')),

    # Activity Calendar
    path('', include(('activity_calendar.urls', 'activity_calendar'), namespace='activity_calendar')),
    # Committee pages
    path('groups/', committee_urls()),
    # Membership File
    path('', include('membership_file.urls')),
    # Redirect all other paths to the core module
    path('', include('core.urls', namespace='core')),

    path('', include('user_interaction.urls', namespace='user_pages')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# NB: 'static(...) above only works when Debug=True! In production, the web server should be set up to serve files
# For production use, view the following:
# https://docs.djangoproject.com/en/3.0/howto/static-files/#serving-files-uploaded-by-a-user
# https://docs.djangoproject.com/en/3.0/howto/static-files/deployment/
#


handler403 = 'core.views.show_error_403'
handler404 = 'core.views.show_error_404'
