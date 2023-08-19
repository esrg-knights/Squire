from django.conf import settings
from django.contrib.auth import views as djangoViews
from django.urls import path, include
from django.views.i18n import JavaScriptCatalog
from martor.views import markdownfy_view

from core.status_collective import registry
from .forms import LoginForm, PasswordResetForm, PasswordResetConfirmForm
from . import views

app_name = "core"

# fmt: off
urlpatterns = [
    # Martor
    path('api/martor/', include([
        path('markdownify/', markdownfy_view, name='martor_markdownify'),
        path('image_uploader/', views.MartorImageUploadAPIView.as_view(), name='martor_image_upload'),
    ])),
    # Login and logout
    path('login', djangoViews.LoginView.as_view(
            template_name='core/user_accounts/login.html',
            extra_context={}, authentication_form=LoginForm,
            redirect_authenticated_user=False), # Setting to True will enable Social Media Fingerprinting.
                                                # For more information, see the corresponding warning at:
                                            #  https://docs.djangoproject.com/en/2.2/topics/auth/default/#all-authentication-views
        name='user_accounts/login'),
    path('logout', djangoViews.LogoutView.as_view(), name='user_accounts/logout'),
    path('logout/success', views.logoutSuccess, name='user_accounts/logout/succes'),
    # Password resets
    # See: https://docs.djangoproject.com/en/2.2/topics/auth/default/#django.contrib.auth.views.PasswordResetView
    path('password_reset', djangoViews.PasswordResetView.as_view(
            success_url='/password_reset/done',
            extra_context={},
            template_name='core/user_accounts/password_reset/password_reset_form.html',
            form_class=PasswordResetForm,
        ),
        name='user_accounts/password_reset'),
    path('password_reset/done', djangoViews.PasswordResetDoneView.as_view(
            template_name='core/user_accounts/password_reset/password_reset_done.html',
            extra_context={},
        ),
        name='user_accounts/password_reset/done'),
    path('password_reset/<uidb64>/<token>', djangoViews.PasswordResetConfirmView.as_view(
            success_url='/password_reset/success',
            extra_context={},
            template_name='core/user_accounts/password_reset/password_reset_confirm.html',
            form_class=PasswordResetConfirmForm,
        ),
        name='user_accounts/password_reset/confirm'),
    path('password_reset/success', djangoViews.PasswordResetCompleteView.as_view(
            template_name='core/user_accounts/password_reset/password_reset_complete.html',
            extra_context={},
        ),
        name='user_accounts/password_reset/success'),
    path('register', views.register, name='user_accounts/register'),
    path('register/success', views.registerSuccess, name='user_accounts/register/success'),
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
