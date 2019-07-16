from django.urls import path
from . import views_api as views

urlpatterns = [
    # The following URLs are not of use currently; administrators can do everything
    # via the Django Admin Panel
    #path('', views.MemberView.as_view(), name='members-api'),
    #path('<int:id>/', views.SpecificMemberView.as_view(), name='member-api'),
]
