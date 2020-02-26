from django.urls import path
from . import views as views

urlpatterns = [
    path('no_member', views.viewNoMember, name='membership_file/no_member'),
    path('account/membership', views.viewOwnMembership, name='membership_file/membership'),
    path('account/membership/edit', views.editOwnMembership, name='membership_file/membership/edit'),
]
