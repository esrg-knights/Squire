from django.urls import include, path

from user_interaction import views


app_name = 'user_interaction'

urlpatterns = [
    path('', views.home_screen, name='homepage'),
]
