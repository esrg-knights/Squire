from django.urls import path
from . import views as views

urlpatterns = [
    path('no_member', views.NotAMemberView.as_view(), name='membership_file/no_member'),
    path('account/membership', views.MemberView.as_view(), name='membership_file/membership'),
    path('account/membership/edit', views.MemberChangeView.as_view(), name='membership_file/membership/edit'),
    path('account/groups', views.viewGroups, name='membership_file/groups'),
]
