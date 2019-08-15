from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext, gettext_lazy as _

# LoginForm that changes the default AuthenticationForm
# It provides a different error message when passing invalid login credentials,
# and allows Inactive users to login
class LoginForm(AuthenticationForm):

    def clean(self):
        # Obtain username and password
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        # Check if both are provided
        self.user_cache = authenticate(self.request, username=username, password=password)
        if self.user_cache is None:
            # Invalid credentials provided
            raise forms.ValidationError(
                _("The username and/or password you specified are not correct."),
                code='ERROR_INVALID_LOGIN',
                params={'username': self.username_field.verbose_name},
            )
        # else:
            # Valid credentials provided
        return self.cleaned_data
