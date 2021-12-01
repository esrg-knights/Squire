from django.urls import include, path

from user_interaction import views
from user_interaction.accountcollective import registry


def user_interaction_urls():
    app_name = 'user_interaction'

    urlpatterns = [
        path('', views.home_screen, name='homepage'),
    ]

    return urlpatterns, app_name, app_name


def user_account_urls():
    app_name = 'account'

    urlpatterns = []
    for setup_config in registry.configs:
        url_key = f'{setup_config.url_keyword}/' if setup_config.url_keyword else ''
        urlpatterns.append(path(url_key, setup_config.urls))

    return urlpatterns, app_name, app_name


urlpatterns = [
    path('', user_interaction_urls()),
    path('account/', user_account_urls()),
]
