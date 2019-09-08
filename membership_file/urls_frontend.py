from django.urls import path
from . import views_frontend as views

urlpatterns = [
    # The following URLs are not of use currently;
    # TODO: Provide a way for members to view (and update) their own membership information
    #path('', views.viewAllMembers, name='members-frontend'),
    #path('<int:id>/', views.viewSpecificMember, name='member-frontend'),
]
