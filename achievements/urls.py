from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('achievements', views.AllAchievementsView.as_view(), name='achievements/all'),
]
