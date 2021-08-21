from django.urls import path, include, reverse_lazy
from django.views.generic.base import RedirectView

from committees.views import *
from committees.models import AssociationGroup


app_name = 'committees'

urlpatterns = [
    # Change Language helper view
    path('', RedirectView.as_view(url=reverse_lazy("committees:committees")), name='home'),
    path('committees/', CommitteeOverview.as_view(), name='committees'),
    path('guilds/', GuildOverview.as_view(), name='guilds'),
    path('boards/', BoardOverview.as_view(), name='boards'),
]
