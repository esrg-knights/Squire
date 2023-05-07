from django.urls import path, include

from . import views as views

# fmt: off
urlpatterns = [
    path('no_member', views.NotAMemberView.as_view(), name='membership_file/no_member'),
    path('continue_membership/', views.ExtendMembershipView.as_view(), name='membership_file/continue_membership'),
    path('continue_membership/success/', views.ExtendMembershipSuccessView.as_view(), name='membership_file/continue_success')
]
