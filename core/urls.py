from django.conf import settings
from django.contrib.auth import views as django_views
from django.urls import path, include
from django.views.i18n import JavaScriptCatalog
from martor.views import markdownfy_view

from core.status_collective import registry
from .forms import PasswordResetForm, PasswordResetConfirmForm
from . import views

app_name = "core"

# fmt: off
urlpatterns = [
    # Login and logout
    path('login', views.LoginView.as_view(), name='user_accounts/login'),
    path('logout', django_views.LogoutView.as_view(), name='user_accounts/logout'),
    path('logout/success/', views.LogoutSuccessView.as_view(), name='user_accounts/logout/success'),
    # Password resets
    # See: https://docs.djangoproject.com/en/3.2/topics/auth/default/#django.contrib.auth.views.PasswordResetView
    path('password_reset', django_views.PasswordResetView.as_view(
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
            form_class=PasswordResetForm,
        ),
        name='user_accounts/password_reset'),
    path('password_reset/done', django_views.PasswordResetDoneView.as_view(
            template_name='core/user_accounts/password_reset/password_reset_done.html',
            extra_context={},
        ),
        name='user_accounts/password_reset/done'),
    path('password_reset/<uidb64>/<token>', django_views.PasswordResetConfirmView.as_view(
            success_url='/password_reset/success',
            extra_context={},
            template_name='core/user_accounts/password_reset/password_reset_confirm.html',
            form_class=PasswordResetConfirmForm,
        ),
        name='user_accounts/password_reset/confirm'),
    path('password_reset/success', django_views.PasswordResetCompleteView.as_view(
            template_name='core/user_accounts/password_reset/password_reset_complete.html',
            extra_context={},
        ),
        name='user_accounts/password_reset/success'),
    path('register', views.RegisterUserView.as_view(), name='user_accounts/register'),
    path('register/success', views.RegisterSuccessView.as_view(), name='user_accounts/register/success'),
    path('newsletters/', views.NewsletterView.as_view(), name='newsletters'),
    path('status/', registry.get_urls()),
    # Mock 403 and 404 views for display testing in development
    path('mock/', include([
        path('500/', views.show_error_500),
        path('404/', views.show_error_404),
        path('403/', views.show_error_403),
    ])),
    # Internalisation library for javascript code. Used by django-recurrence
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
]
