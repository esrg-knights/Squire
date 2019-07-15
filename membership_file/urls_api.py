from django.urls import path
from . import views_api as views

urlpatterns = [
    path('', views.MemberView.as_view(), name='members-api'),
    path('<int:id>/', views.SpecificMemberView.as_view(), name='member-api'),
]
