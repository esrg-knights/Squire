from django.urls import path, include

from . import views as views

urlpatterns = [
    path('no_member', views.NotAMemberView.as_view(), name='membership_file/no_member'),
]
