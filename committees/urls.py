from django.urls import path, include, reverse_lazy
from django.views.generic.base import RedirectView

from committees.views import *
from committees.committeecollective import registry


def get_urls():
    """
    Go over all installed apps and look for the urls file in the setup folder.
    This way we can assign the relevant setup views and the like to the modules instead of dumping it through
    a chain of apps.

    :return:
    """

    def associationgroup_pages_urls():
        urlpatterns = []
        for setup_config in registry.configs:
            url_key = f'{setup_config.url_keyword}/' if setup_config.url_keyword else ''
            urlpatterns.append(path(url_key, setup_config.urls))

        return urlpatterns, None, None

    urls = [
        # Change Language helper view
        path('', RedirectView.as_view(url=reverse_lazy("committees:committees")), name='home'),
        path('committees/', CommitteeOverview.as_view(), name='committees'),
        path('guilds/', GuildOverview.as_view(), name='guilds'),
        path('boards/', BoardOverview.as_view(), name='boards'),
        path('<int:group_id>/', associationgroup_pages_urls())  # include([
    ]


    return urls, 'committees', 'committees'
