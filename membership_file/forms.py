from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Member, Room

##################################################################################
# Defines forms related to the membership file.
# @since 05 FEB 2020
##################################################################################

class RequestUserForm():

    user = None

    def __init__(self, *args, user=None, **kwargs):
        # User that created the form (request.user in the relevant view)
        self.user = user

        # We explicitly do not pass 'user' down the Form-chain,
        #   as it's an unexpected kwarg (for some Forms)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.last_updated_by = self.user

        if commit:
            instance.save()
        return instance

class MemberRoomForm(forms.ModelForm):
    """
    ModelForm that adds an additional multiple select field for managing
    the rooms that members have access to.
    """
    accessible_rooms = forms.ModelMultipleChoiceField(
        Room.objects.all(),
        widget=admin.widgets.FilteredSelectMultiple('Rooms', False),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Set initial values (not needed if creating a new instance)
            initial_rooms = self.instance.accessible_rooms.values_list('pk', flat=True)
            self.initial['accessible_rooms'] = initial_rooms

        # Remove Room-fields if they're in the 'exclude'-list
        for exclude_field in ['accessible_rooms']:
            if exclude_field in self.Meta.exclude:
                del self.fields[exclude_field]

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()
            self.save_m2m()
        else:
            # Defer saving the m2m-relation; the member might not yet exist at this point
            self.save_m2m = self._save_m2m
        return instance

    def _save_m2m(self):
        super()._save_m2m()
        for field in ['accessible_rooms']:
            if field not in self.Meta.exclude:
                getattr(self.instance, field).clear()
                getattr(self.instance, field).add(*self.cleaned_data[field])


class AdminMemberForm(RequestUserForm, MemberRoomForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Disable all fields if the member is marked for deletion
        if self.instance.marked_for_deletion:
            for field in self.fields:
                self.fields[field].disabled = True
            self.fields['marked_for_deletion'].disabled = False


# A form that allows a member to be updated or created
class MemberForm(RequestUserForm, MemberRoomForm):
    class Meta:
        model = Member
        exclude = ('last_updated_by', 'last_updated_date', 'marked_for_deletion', 'user', 'notes', 'is_deregistered')
        readonly_fields = ['accessible_rooms', 'member_since', 'has_paid_membership_fee', 'is_honorary_member', 'external_card_deposit', 'key_id']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make fields marked as 'readonly' actually readonly
        #   Note that Django automagically ignores these fields as well
        #   in case they are tampered with by the client
        for field in self.Meta.readonly_fields:
            if field not in self.fields:
                raise ImproperlyConfigured(
                    "Field %s does not exist; form %s "
                    % (field, self.__class__.__name__)
                )
            self.fields[field].disabled = True

            # Also set a placeholder for uneditable fields to avoid
            #   confusion for uneditable empty values
            self.fields[field].widget.attrs['placeholder'] = "(None)"

    def is_valid(self):
        ret = forms.Form.is_valid(self)
        # Add an 'error' class to input elements that contain an error
        for field in self.errors:
            self.fields[field].widget.attrs.update({'class': self.fields[field].widget.attrs.get('class', '') + ' alert-danger'})
        return ret
