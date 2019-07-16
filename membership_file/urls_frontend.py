from django.urls import path
from . import views_frontend as views

urlpatterns = [
    # The following URLs are not of use currently; users updating their own
    # information is not within the scope of this branch
    #path('', views.viewAllMembers, name='members-frontend'),
    #path('<int:id>/', views.viewSpecificMember, name='member-frontend'),
]
