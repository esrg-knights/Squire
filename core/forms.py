from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import (AuthenticationForm, UserCreationForm,
    PasswordChangeForm as DjangoPasswordChangeForm, PasswordResetForm as DjangoPasswordResetForm,
    SetPasswordForm as DjangoPasswordResetConfirmForm)
from django.core.exceptions import ValidationError
from django.utils.translation import gettext, gettext_lazy as _

from .util import add_form_control_class
from .models import ExtendedUser as User

##################################################################################
# Defines general-purpose forms.
# @since 15 AUG 2019
##################################################################################


# LoginForm that changes the default AuthenticationForm
# It provides a different error message when passing invalid login credentials,
# and allows Inactive users to login
class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        add_form_control_class(LoginForm, self, *args, **kwargs)

    def clean(self):
        # Obtain username and password
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        # Check if both are provided
        if username and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                # Invalid credentials provided
                self.add_error(None, ValidationError(
                    _("The username and/or password you specified are not correct."),
                    code='ERROR_INVALID_LOGIN',
                    params={'username': self.username_field.verbose_name},
                ))
                return
            # else:
                # Valid credentials provided
        return self.cleaned_data


# RegisterForm that expands on the default UserCreationForm
# It requires a (unique) email address, and includes an optional nickname field
class RegisterForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        add_form_control_class(RegisterForm, self, *args, **kwargs)

    email = forms.EmailField(label = "Email")
    nickname = forms.CharField(label = "Nickname", required=False, help_text='A nickname (if provided) is shown instead of your username.')

    class Meta:
        model = User
        fields = ("username", "nickname", "email", )

    def clean_email(self):
        # Ensure that another user with the same email does not exist
        cleaned_email = self.cleaned_data.get('email')
        if User.objects.filter(email=cleaned_email).exists():
            self.add_error('email', ValidationError(
                _("A user with that email address already exists."),
                code='ERROR_EMAIL_EXISTS',
            ))
        return cleaned_email

    def save(self, commit=True):
        user = super(RegisterForm, self).save(commit=False)
        # First name field is used as a nickname field
        user.first_name = self.cleaned_data["nickname"]
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()
        return user

# Adds the relevant bootstrap classes to the password change form
class PasswordChangeForm(DjangoPasswordChangeForm):
    def __init__(self, *args, **kwargs):
        add_form_control_class(PasswordChangeForm, self, *args, **kwargs)

# Adds the relevant bootstrap classes to the password reset form
class PasswordResetForm(DjangoPasswordResetForm):
    def __init__(self, *args, **kwargs):
        add_form_control_class(PasswordResetForm, self, *args, **kwargs)

class PasswordResetConfirmForm(DjangoPasswordResetConfirmForm):
    def __init__(self, *args, **kwargs):
        add_form_control_class(PasswordResetConfirmForm, self, *args, **kwargs)
