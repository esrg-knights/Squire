from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('aaa', views.viewAllAchievements, name='achievements-frontend'),
    path('aaa<int:id>/', views.viewSpecificAchievement, name='achievement-frontend'),

    path('aaacategories/', views.viewAllCategories, name='categories-frontend'),
    path('aaacategories/<int:id>/', views.viewSpecificCategory, name='category-frontend'),

    path('aaamembers/<int:id>/', views.viewSpecificMember, name='achievement-member-frontend'),

    path('account/achievements/', views.viewAchievementsUser, name='achievements/user'),
    path('achievements/', views.viewAchievementsAll, name='achievements/all'),
]
