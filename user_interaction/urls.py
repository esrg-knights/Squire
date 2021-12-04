from django.urls import include, path

from user_interaction import views
from user_interaction.accountcollective import registry


def user_interaction_urls():
    app_name = 'user_interaction'

    urlpatterns = [
        path('', views.home_screen, name='homepage'),
    ]
    return urlpatterns, app_name, app_name


urlpatterns = [
    path('', user_interaction_urls()),
    path('account/', registry.get_urls()),
]
