from django.urls import path

from membership_file import views

app_name = "membership"

urlpatterns = [
    path("no_member", views.NotAMemberView.as_view(), name="no_member"),
    path("continue_membership/", views.ExtendMembershipView.as_view(), name="continue_membership"),
    path(
        "continue_membership/success/",
        views.ExtendMembershipSuccessView.as_view(),
        name="continue_success",
    ),
    # NB: The following two paths should be above the path for link_account/confirm
    path(
        "link_account/<uidb64>/register/",
        views.LinkMembershipRegisterView.as_view(),
        name="link_account/register",
    ),
    path(
        "link_account/<uidb64>/login/",
        views.LinkMembershipLoginView.as_view(),
        name="link_account/login",
    ),
    path(
        "link_account/<uidb64>/<token>/",
        views.LinkMembershipConfirmView.as_view(),
        name="link_account/confirm",
    ),
]
