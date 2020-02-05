from django import forms
from django.contrib.auth.models import User
from django.forms import ModelForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext, gettext_lazy as _

from .models import Member

##################################################################################
# Defines forms related to the membership file.
# @author E.M.A. Arts
# @since 05 FEB 2020
##################################################################################


# A form that allows a member to be updated or created
class MemberForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            # Add Bootstrap css
            visible.field.widget.attrs['class'] = 'form-control'

    class Meta:
        model = Member
        fields = "__all__"

    def save(self, commit=True):
        pass
