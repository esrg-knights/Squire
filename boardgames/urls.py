from django.urls import path, include

from boardgames.views import *



app_name = 'boardgames'

urlpatterns = [
    # Change Language helper view
    path('', BoardGameView.as_view(), name='home'),
]
