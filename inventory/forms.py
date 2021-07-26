import datetime
from django import forms
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError


from membership_file.models import Member
from inventory.models import *

__all__ = ['OwnershipRemovalForm', 'OwnershipActivationForm', 'OwnershipNoteForm', 'OwnershipCommitteeForm',
           'AddOwnershipCommitteeLink', 'AddOwnershipMemberLink']


class OwnershipRemovalForm(forms.Form):
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


class OwnershipActivationForm(forms.Form):
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


class OwnershipNoteForm(forms.ModelForm):
    class Meta:
        model = Ownership
        fields = ['note']


class OwnershipCommitteeForm(forms.ModelForm):
    class Meta:
        model = Ownership
        fields = ['note', 'added_since']


class AddOwnerShipLinkMixin:
    def __init__(self, *args, item=None, user=None, **kwargs):
        super(AddOwnerShipLinkMixin, self).__init__(*args, **kwargs)
        self.instance.content_object = item
        self.instance.added_by = user



class AddOwnershipCommitteeLink(AddOwnerShipLinkMixin, forms.ModelForm):
    committee = forms.ModelChoiceField(queryset=Group.objects.none())

    class Meta:
        model = Ownership
        fields = ['committee', 'note', 'is_active']

    def __init__(self, *args, **kwargs):
        super(AddOwnershipCommitteeLink, self).__init__(*args, **kwargs)
        self.fields['committee'].queryset = self.instance.added_by.groups.all()
        if self.instance.added_by.groups.count() == 1:
            self.fields['committee'].initial = self.instance.added_by.groups.first().id
            self.fields['committee'].disabled = True

    def clean(self):
        self.instance.group = self.cleaned_data['committee']
        return super(AddOwnershipCommitteeLink, self).clean()


class AddOwnershipMemberLink(AddOwnerShipLinkMixin, forms.ModelForm):
    member = forms.ModelChoiceField(queryset=Member.objects.filter(is_deregistered=False).order_by('first_name'))

    class Meta:
        model = Ownership
        fields = ['member', 'note', 'is_active']


    def clean(self):
        self.instance.member = self.cleaned_data['member']
        return super(AddOwnershipMemberLink, self).clean()



