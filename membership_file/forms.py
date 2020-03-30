from django import forms
from django.forms import ModelForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext, gettext_lazy as _

from .models import Member
from .models import MemberUser as User

##################################################################################
# Defines forms related to the membership file.
# @since 05 FEB 2020
##################################################################################


# A form that allows a member to be updated or created
class MemberForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            # Add Bootstrap css
            visible.field.widget.attrs['class'] = 'form-control'

    def is_valid(self):
        ret = forms.Form.is_valid(self)
        # Add an 'error' class to input elements that contain an error
        for field in self.errors:
            self.fields[field].widget.attrs.update({'class': self.fields[field].widget.attrs.get('class', '') + ' alert-danger'})
        return ret

    class Meta:
        model = Member
        exclude = ('last_updated_by', 'marked_for_deletion', 'user')
