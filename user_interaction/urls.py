from django.urls import include, path

from user_interaction import views, config


def user_interaction_urls():
    app_name = 'user_interaction'

    urlpatterns = [
        path('', views.home_screen, name='homepage'),
    ]

    return urlpatterns, app_name, app_name


def user_account_urls():
    app_name = 'account'

    urlpatterns = [
        path('preferences', views.UpdateUserPreferencesView.as_view(), name='change_preferences')
    ]
    for setup_config in config.get_all_configs():
        url_key = f'{setup_config.url_keyword}/' if setup_config.url_keyword else ''
        urlpatterns.append(path(url_key, setup_config.urls))

    print(urlpatterns)

    return urlpatterns, app_name, app_name


urlpatterns = [
    path('', user_interaction_urls()),
    path('account/', user_account_urls()),
]
