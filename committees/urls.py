from django.urls import path, include

from committees.views import *



app_name = 'committees'

urlpatterns = [
    # Change Language helper view
    path('', AssocGroupOverview.as_view(), name='home'),
]
