from django.urls import path, include

from inventory.views import *

namespace = 'inventory'

urlpatterns = [
    # Change Language helper view
    path('', BoardgameView.as_view(), name='home'),
]
