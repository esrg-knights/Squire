from django.urls import path
from . import views as views
from django.contrib.auth import views as djangoViews
from .forms import LoginForm


urlpatterns = [
    path('login/', djangoViews.LoginView.as_view(
            template_name='core/user_accounts/login.html',
            extra_context={}, authentication_form=LoginForm,
            redirect_authenticated_user=False), # Setting to True will enable Social Media Fingerprinting.
                                                # For more information, see the corresponding warning at:
                                            #  https://docs.djangoproject.com/en/2.2/topics/auth/default/#all-authentication-views
        name='core/user_accounts/login'),

    path('logout/', djangoViews.LogoutView.as_view(), name='core/user_accounts/logout'),
    path('logout/success', views.logoutSuccess, name='core/user_accounts/logout/succes'),
    
    path('account', views.viewAccount, name='core/user_accounts/account'),
    path('', views.homePage, name='core/homepage'),
]
