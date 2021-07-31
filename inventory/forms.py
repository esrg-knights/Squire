from django import forms
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils import timezone


from membership_file.models import Member
from inventory.models import *

__all__ = ['OwnershipRemovalForm', 'OwnershipActivationForm', 'OwnershipNoteForm', 'OwnershipCommitteeForm',
           'AddOwnershipCommitteeLinkForm', 'AddOwnershipMemberLinkForm', 'FilterOwnershipThroughRelatedItems',
           'DeleteItemForm']


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
    committee = forms.ModelChoiceField(queryset=Group.objects.none(), required=True)

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
        self.instance.group = self.cleaned_data.get('committee', None)
        return super(AddOwnershipCommitteeLinkForm, self).clean()


class AddOwnershipMemberLinkForm(AddOwnerShipLinkMixin, forms.ModelForm):
    member = forms.ModelChoiceField(
        required=True,
        queryset=Member.objects.filter(is_deregistered=False).order_by('first_name')
    )

    class Meta:
        model = Ownership
        fields = ['member', 'note', 'is_active']

    def clean(self):
        self.instance.member = self.cleaned_data.get('member', None)
        return super(AddOwnershipMemberLinkForm, self).clean()



class FilterOwnershipThroughRelatedItems(forms.Form):
    search_field = forms.CharField(max_length=100, required=False)

    def get_filtered_items(self, queryset):
        item_types = [BoardGame]

        ownerships = Ownership.objects.none()

        for item_type in item_types:
            content_type = ContentType.objects.get_for_model(item_type)

            sub_items = item_type.objects.filter(name__icontains=self.cleaned_data['search_field'])
            sub_ownerships = queryset.filter(
                content_type=content_type,
                object_id__in=sub_items.values_list('id', flat=True)
            )
            ownerships = ownerships.union(sub_ownerships)
        return ownerships

class DeleteItemForm(forms.Form):

    def __init__(self, *args, item=None, ignore_active_links, **kwargs):
        """
        Form for the deletion of items
        :param args:
        :param user: The user that tries to delete it
        :param kwargs:
        """
        self.item = item
        self.ignore_active_links = ignore_active_links
        super(DeleteItemForm, self).__init__(*args, **kwargs)

    def clean(self):
        if not self.ignore_active_links:
            if self.item.currently_in_possession().exists():
                raise ValidationError("There are currently {number} instances of this item at the association."
                                      "You are not allowed to remove this without deleting those first",
                                      code='active_ownerships')

    def delete_item(self):
        self.item.delete()





