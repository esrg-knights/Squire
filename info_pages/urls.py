from django.urls import path, include

from info_pages.views import InfoPageView



app_name = 'info_pages'

urlpatterns = [
    # Change Language helper view
    path('', InfoPageView.as_view(), name='home'),
]