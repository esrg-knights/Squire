from django.urls import path
from . import views

urlpatterns = [
    path('', views.viewAllMembers, name='members-frontend'),
    path('<int:id>/', views.viewSpecificMember, name='member-frontend'),
]
