from django import forms
from django.forms import ModelForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext, gettext_lazy as _

from .models import ActivitySlot
from core.models import PresetImage

##################################################################################
# Defines forms related to the membership file.
# @since 28 AUG 2020
##################################################################################


# A form that allows activity-slots to be created
class ActivitySlotForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.fields['image'].queryset = PresetImage.objects.filter(selectable=True)
        self.fields['image'].label_from_instance = lambda image: image.name

    def is_valid(self):
        ret = forms.Form.is_valid(self)

        # Users can only create slots for at least 1 participant
        # NB: At this point the data is a string
        if self.data['max_participants'] == '0':
            self.errors.update({'max_participants': ['A slot cannot have 0 participants']})
            ret = False

        # Add an 'error' class to input elements that contain an error
        for field in self.errors:
            self.fields[field].widget.attrs.update({'class': self.fields[field].widget.attrs.get('class', '') + ' alert-danger'})
        return ret

    class Meta:
        model = ActivitySlot
        fields = "__all__"
