from django import forms
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils import timezone


from membership_file.models import Member
from inventory.models import *

__all__ = ['OwnershipRemovalForm', 'OwnershipActivationForm', 'OwnershipNoteForm', 'OwnershipCommitteeForm',
           'AddOwnershipCommitteeLinkForm', 'AddOwnershipMemberLinkForm']


class OwnershipRemovalForm(forms.Form):
    """ Fieldless form to allow members to set a loaned item as taken home """
    def __init__(self, *args, ownership=None, **kwargs):
        super(OwnershipRemovalForm, self).__init__(*args, **kwargs)
        self.ownership = ownership

    def save(self):
        self.ownership.is_active = False
        self.ownership.added_since = timezone.now().date()
        self.ownership.save()

    def clean(self):
        if not self.ownership.is_active:
            raise ValidationError('This item was already taken home', code='invalid')
        return self.cleaned_data


class OwnershipActivationForm(forms.Form):
    """ Fieldless form to allow members to re-loan their items to the association """

    def __init__(self, *args, ownership=None, **kwargs):
        super(OwnershipActivationForm, self).__init__(*args, **kwargs)
        self.ownership = ownership

    def save(self):
        self.ownership.is_active = True
        self.ownership.added_since = timezone.now().date()
        self.ownership.save()

    def clean(self):
        if self.ownership.is_active:
            raise ValidationError('This item was already at the Knights', code='invalid')

        return self.cleaned_data


class OwnershipNoteForm(forms.ModelForm):
    """ Form used by members to adjust the written note at their owned items """
    class Meta:
        model = Ownership
        fields = ['note']


class OwnershipCommitteeForm(forms.ModelForm):
    """ Form used by groups/committees to adjust ownership data """
    class Meta:
        model = Ownership
        fields = ['note', 'added_since']


class AddOwnerShipLinkMixin:
    """ Simple mixin that sets Ownership instance settings """
    def __init__(self, *args, item=None, user=None, **kwargs):
        super(AddOwnerShipLinkMixin, self).__init__(*args, **kwargs)
        self.instance.content_object = item
        self.instance.added_by = user


class AddOwnershipCommitteeLinkForm(AddOwnerShipLinkMixin, forms.ModelForm):
    committee = forms.ModelChoiceField(queryset=Group.objects.none())

    class Meta:
        model = Ownership
        fields = ['committee', 'note', 'is_active']

    def __init__(self, *args, **kwargs):
        super(AddOwnershipCommitteeLinkForm, self).__init__(*args, **kwargs)
        # Adjust committee field depending on the number of groups a user is in.
        # There is no reason to change group if only one is possible
        self.fields['committee'].queryset = self.instance.added_by.groups.all()
        if self.instance.added_by.groups.count() == 1:
            self.fields['committee'].initial = self.instance.added_by.groups.first().id
            self.fields['committee'].disabled = True

    def clean(self):
        self.instance.group = self.cleaned_data['committee']
        return super(AddOwnershipCommitteeLinkForm, self).clean()


class AddOwnershipMemberLinkForm(AddOwnerShipLinkMixin, forms.ModelForm):
    member = forms.ModelChoiceField(queryset=Member.objects.filter(is_deregistered=False).order_by('first_name'))

    class Meta:
        model = Ownership
        fields = ['member', 'note', 'is_active']

    def clean(self):
        self.instance.member = self.cleaned_data['member']
        return super(AddOwnershipMemberLinkForm, self).clean()



