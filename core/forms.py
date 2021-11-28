from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.forms import (AuthenticationForm, UserCreationForm,
    PasswordChangeForm as DjangoPasswordChangeForm, PasswordResetForm as DjangoPasswordResetForm,
    SetPasswordForm as DjangoPasswordResetConfirmForm)
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.forms.fields import Field
from django.http.response import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from martor.widgets import MartorWidget

from core.models import MarkdownImage
from core.pins import Pin
from core.widgets import  ImageUploadMartorWidget
from utils.forms import UpdatingUserFormMixin

from django.contrib.auth import get_user_model
User = get_user_model()

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

##################################################################################
# Markdown
##################################################################################

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

##################################################################################
# Pins
# @since 28 NOV 2021
##################################################################################

class PinnableForm(forms.Form):
    """
        Form used by PinnableFormMixin that allows (un)pinning
        a model instance based on the value of `do_pin`.
    """
    do_pin = forms.BooleanField(
        required=False,
        # widget=forms.HiddenInput()
    )


class PinnableFormMixin:
    """
        Mixin that adds a form to the view that allows pinning a model instance
        currently in the View. It can be used alongside any other form in the
        same View.

        `pinnable_prefix` allows changing the way this form is
        represented within the context.
    """
    pinnable_prefix = "pinnable_form"

    def __init__(self, *args, **kwargs):
        self.pinnable_instance = None

    def post(self, request, *args, **kwargs):
        if self.pinnable_prefix not in self.request.POST:
            # The "pin" form was not submitted; so another form was
            #   submitted instead. Call the parent's post method instead.
            return super().post(request, *args, **kwargs)

        if not self.request.user.has_perm('core.change_pin'):
            # User must be able to pin things
            return self.handle_no_permission()

        # The instance was (un)pinned
        pinnable_form = self.get_pinnable_form(data=self.request.POST)
        if pinnable_form.is_valid():
            # Correctly (un)pinned
            return self.pinnable_form_valid(pinnable_form.cleaned_data['do_pin'])
        # Something went wrong
        return self.pinnable_form_invalid()

    def pinnable_form_valid(self, was_pinned):
        """ The form used to (un)pin the item was valid """
        if was_pinned:
            self.create_pin()
            message = _("'{pinnable_instance}' was successfully pinned!")
        else:
            self.delete_pin()
            message = _("'{pinnable_instance}' was successfully unpinned!")

        messages.success(self.request, message.format(pinnable_instance=str(self.pinnable_instance).capitalize()))
        return HttpResponseRedirect(self.request.get_full_path())

    def pinnable_form_invalid(self):
        """ The form used to (un)pin the item was invalid """
        messages.error(self.request, f"An unexpected error occurred when trying to pin {str(self.pinnable_instance)}. Please try again later.")
        return HttpResponseRedirect(self.request.get_full_path())

    def get_pinnable_instance(self):
        """
            Fetches the model instance to which a new pin will be attached, or
            from which all pins should be removed, depending on the value of the
            submitted form.
        """
        raise NotImplementedError("Subclasses should override this method")

    def create_pin(self):
        """ Creates a pin for the attached model instance """
        if self.is_instance_pinned():
            # There technically is a race condition here if two users pin the object at the exact same time
            return
        Pin.objects.create(content_object=self.pinnable_instance, category="auto-pin", author=self.request.user)

    def delete_pin(self):
        """ Removes all (automatically created) pins attached to this model instance """
        self.pinnable_instance.pins.filter(category="auto-pin").delete()

    def is_instance_pinned(self):
        """ Returns whether the attached model instance is currently pinned """
        return self.pinnable_instance.pins.exists()

    def get_pinnable_form(self, **kwargs):
        """ Gets the form used to determine whether to pin or unpin the attached model instance """
        self.pinnable_instance = self.get_pinnable_instance()
        new_kwargs = {
            'initial': {
                'do_pin': not self.is_instance_pinned(),
            },
            # We need a different prefix to prevent overlap with other
            #   forms that may also be in the same view.
            'prefix': self.pinnable_prefix,
        }
        new_kwargs.update(**kwargs)
        return PinnableForm(**new_kwargs)

    def get_context_data(self, **kwargs):
        """ Insert the pinnable form into the context dict. """
        if self.pinnable_prefix not in kwargs:
            kwargs[self.pinnable_prefix] = self.get_pinnable_form()
        return super().get_context_data(**kwargs)
