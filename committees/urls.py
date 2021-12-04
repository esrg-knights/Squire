from django.urls import path, include, reverse_lazy
from django.views.generic.base import RedirectView

from committees.views import *
from committees.committeecollective import registry


app_name = 'committees'

urlpatterns = [
    path('', RedirectView.as_view(url=reverse_lazy("committees:committees")), name='home'),
    path('committees/', CommitteeOverview.as_view(), name='committees'),
    path('guilds/', GuildOverview.as_view(), name='guilds'),
    path('boards/', BoardOverview.as_view(), name='boards'),
    path('<int:group_id>/', registry.get_urls(with_namespace=False)),
]
