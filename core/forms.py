from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import (AuthenticationForm, UserCreationForm,
    PasswordChangeForm as DjangoPasswordChangeForm, PasswordResetForm as DjangoPasswordResetForm,
    SetPasswordForm as DjangoPasswordResetConfirmForm)
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.forms.fields import Field
from django.utils.translation import gettext_lazy as _
from martor.widgets import MartorWidget

from .models import ExtendedUser as User
from core.models import MarkdownImage
from core.widgets import  ImageUploadMartorWidget
from utils.forms import UpdatingUserFormMixin

##################################################################################
# Defines general-purpose forms.
# @since 15 AUG 2019
##################################################################################


# LoginForm that changes the default AuthenticationForm
# It provides a different error message when passing invalid login credentials,
# and allows Inactive users to login
class LoginForm(AuthenticationForm):
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
# It requires a (unique) email address, and includes a required real_name field
class RegisterForm(UserCreationForm):
    email = forms.EmailField(label = "Email")
    real_name = forms.CharField(label="Real Name", help_text='Your real name will be shown instead of your username when you register for activities.')

    class Meta:
        model = User
        fields = ("username", "real_name", "email")

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
        # First name field is used as a real_name field
        user.first_name = self.cleaned_data["real_name"]
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()
        return user

# Adds the relevant bootstrap classes to the password change form
class PasswordChangeForm(DjangoPasswordChangeForm):
    pass

# Adds the relevant bootstrap classes to the password reset form
class PasswordResetForm(DjangoPasswordResetForm):
    pass

class PasswordResetConfirmForm(DjangoPasswordResetConfirmForm):
    pass

class MarkdownForm(ModelForm):
    """
        Changes the model's fields that support Markdown such that they use a variant of Martor's
        widget that also allows images to be uploaded. Furthermore, it allows those fields to
        display a placeholder, just like normal HTML inputs.

        Also ensures that any images uploaded through Martor's widget are properly linked
        to the object that is being edited (if any). If an image is uploaded for an object
        that does not yet exist, then these images are temporarily unlinked (and do not reference)
        any object. Upon saving, if such "orphan" images exist (for the current model, and uploaded by
        the current user), they are linked to the newly created instance.
    """
    placeholder_detail_title = "Field %s"

    is_new_instance = True

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.is_new_instance = self.instance.id is None

        for boundfield in self.visible_fields():
            if isinstance(boundfield.field.widget, MartorWidget):
                self._give_field_md_widget(boundfield.field)

    def _give_field_md_widget(self, field: Field):
        """ Gives the given field an ImageUploadMartorWidget """
        # Add the field's label to the placeholder title
        label = field.label
        placeholder_title = self.placeholder_detail_title % label.capitalize()
        field.widget = ImageUploadMartorWidget(
            ContentType.objects.get_for_model(self.instance),
            self.instance.id, placeholder_detail_title=placeholder_title
        )

    def _save_m2m(self):
        super()._save_m2m()

        # Handle "orphan" images that were uploaded when the instance was not yet saved
        #   to the database.
        if self.is_new_instance and self.user is not None:
            # Assign MarkdownImages for this contenttype, and uploaded by the requesting user
            content_type = ContentType.objects.get_for_model(self.instance)
            MarkdownImage.objects.filter(content_type=content_type, object_id__isnull=True, uploader=self.user).update(
                object_id=self.instance.id,
                uploader=self.user
            )

class MarkdownImageAdminForm(UpdatingUserFormMixin, ModelForm):
    class Meta:
        model = MarkdownImage
        fields = "__all__"

    updating_user_field_name = "uploader"
