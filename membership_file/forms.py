from django import forms
from django.contrib import admin
from django.forms import ModelForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext, gettext_lazy as _

from .models import Member, Room
from .models import MemberUser as User

##################################################################################
# Defines forms related to the membership file.
# @since 05 FEB 2020
##################################################################################


# A form that allows a member to be updated or created
class MemberForm(ModelForm):
    def is_valid(self):
        ret = forms.Form.is_valid(self)
        # Add an 'error' class to input elements that contain an error
        for field in self.errors:
            self.fields[field].widget.attrs.update({'class': self.fields[field].widget.attrs.get('class', '') + ' alert-danger'})
        return ret

    class Meta:
        model = Member
        exclude = ('last_updated_by', 'marked_for_deletion', 'user')


class RoomAdminForm(forms.ModelForm):
    """
    ModelForm that adds an additional multiple select field for managing
    the rooms that members have access to.
    """
    accessible_rooms = forms.ModelMultipleChoiceField(
        Room.objects.all(),
        widget=admin.widgets.FilteredSelectMultiple('Rooms', False),
        required=False,
    )
    normally_accessible_rooms = forms.ModelMultipleChoiceField(
        Room.objects.all(),
        widget=admin.widgets.FilteredSelectMultiple('Rooms', False),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            initial_rooms = self.instance.accessible_rooms.values_list('pk', flat=True)
            self.initial['accessible_rooms'] = initial_rooms
            initial_removed_rooms = self.instance.normally_accessible_rooms.values_list('pk', flat=True)
            self.initial['normally_accessible_rooms'] = initial_removed_rooms


    def save(self, *args, **kwargs):
        kwargs['commit'] = True
        return super().save(*args, **kwargs)


    def save_m2m(self):
        self.instance.accessible_rooms.clear()
        self.instance.accessible_rooms.add(*self.cleaned_data['accessible_rooms'])
        self.instance.normally_accessible_rooms.clear()
        self.instance.normally_accessible_rooms.add(*self.cleaned_data['normally_accessible_rooms'])
        