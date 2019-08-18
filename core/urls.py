from django.urls import path
from django.conf import settings
from django.contrib.auth import views as djangoViews
from .forms import LoginForm
from . import views as views


urlpatterns = [
    # Login and logout
    path('login', djangoViews.LoginView.as_view(
            template_name='core/user_accounts/login.html',
            extra_context={}, authentication_form=LoginForm,
            redirect_authenticated_user=False), # Setting to True will enable Social Media Fingerprinting.
                                                # For more information, see the corresponding warning at:
                                            #  https://docs.djangoproject.com/en/2.2/topics/auth/default/#all-authentication-views
        name='core/user_accounts/login'),
    path('logout', djangoViews.LogoutView.as_view(), name='core/user_accounts/logout'),
    path('logout/success', views.logoutSuccess, name='core/user_accounts/logout/succes'),
    # Password resets
    # See: https://docs.djangoproject.com/en/2.2/topics/auth/default/#django.contrib.auth.views.PasswordResetView
    path('password_reset', djangoViews.PasswordResetView.as_view(
            success_url='/password_reset/done',
            extra_context={},
            template_name='core/user_accounts/password_reset/password_reset_form.html',
            subject_template_name='core/user_accounts/password_reset/password_reset_subject.txt',
            email_template_name='core/user_accounts/password_reset/password_reset_email.txt',
            extra_email_context={
                'committee_name': settings.COMMITTEE_FULL_NAME,
                'committee_abbreviation': settings.COMMITTEE_ABBREVIATION,
                'application_name': settings.APPLICATION_NAME,
            },
        ),
        name='core/user_accounts/password_reset'),
    path('password_reset/done', djangoViews.PasswordResetDoneView.as_view(
            template_name='core/user_accounts/password_reset/password_reset_done.html',
            extra_context={},
        ),
        name='core/user_accounts/password_reset/done'),
    path('password_reset/<uidb64>/<token>', djangoViews.PasswordResetConfirmView.as_view(
            success_url='/password_reset/success',
            extra_context={},
            template_name='core/user_accounts/password_reset/password_reset_confirm.html',
        ),
        name='core/user_accounts/password_reset/confirm'),
    path('password_reset/success', djangoViews.PasswordResetCompleteView.as_view(
            template_name='core/user_accounts/password_reset/password_reset_complete.html',
            extra_context={},
        ),
        name='core/user_accounts/password_reset/success'),
    # Password change
    path('account/password_change', djangoViews.PasswordChangeView.as_view(
            template_name='core/user_accounts/password_change/password_change_form.html',
            extra_context={},
            success_url='password_change/success',
        ),
        name='core/user_accounts/password_change'),
    path('account/password_change/success', djangoViews.PasswordChangeDoneView.as_view(
            template_name='core/user_accounts/password_change/password_change_done.html',
            extra_context={},
        ),
        name='core/user_accounts/password_change/success'),
    # Other pages
    path('account', views.viewAccount, name='core/user_accounts/account'),
    path('', views.homePage, name='core/homepage'),
]
