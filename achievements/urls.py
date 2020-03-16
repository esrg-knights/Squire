from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('account/achievements', views.viewAchievementsUser, name='achievements/user'),
    path('achievements', views.viewAchievementsAll, name='achievements/all'),
]
