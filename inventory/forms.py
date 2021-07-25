import datetime
from django.forms import Form, ValidationError


from inventory.models import *

__all__ = ['OwnershipRemovalForm', 'OwnershipActivationForm']


class OwnershipRemovalForm(Form):
    def __init__(self, *args, ownership=None, **kwargs):
        super(OwnershipRemovalForm, self).__init__(*args, **kwargs)
        self.ownership = ownership

    def save(self):
        self.ownership.is_active = False
        self.ownership.added_since = datetime.date.today()
        self.ownership.save()

    def clean(self):
        if not self.ownership.is_active:
            raise ValidationError('This item was already taken home', code='invalid')
        return self.cleaned_data


class OwnershipActivationForm(Form):
    def __init__(self, *args, ownership=None, **kwargs):
        super(OwnershipActivationForm, self).__init__(*args, **kwargs)
        self.ownership = ownership

    def save(self):
        self.ownership.is_active = True
        self.ownership.added_since = datetime.date.today()
        self.ownership.save()

    def clean(self):
        if self.ownership.is_active:
            raise ValidationError('This item was already at the Knights', code='invalid')

        return self.cleaned_data




