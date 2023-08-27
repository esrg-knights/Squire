from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils.translation import gettext_lazy as _

from utils.widgets import OtherRadioSelect

from .models import Member, Room, MemberYear, Membership
from utils.forms import UpdatingUserFormMixin

##################################################################################
# Defines forms related to the membership file.
# @since 05 FEB 2020
##################################################################################


class MemberRoomForm(forms.ModelForm):
    """
    ModelForm that adds an additional multiple select field for managing
    the rooms that members have access to.
    """

    accessible_rooms = forms.ModelMultipleChoiceField(
        Room.objects.all(),
        widget=FilteredSelectMultiple("Rooms", False),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Set initial values (not needed if creating a new instance)
            initial_rooms = self.instance.accessible_rooms.values_list("pk", flat=True)
            self.initial["accessible_rooms"] = initial_rooms

    def _save_m2m(self):
        super()._save_m2m()
        self.instance.accessible_rooms.clear()
        self.instance.accessible_rooms.add(*self.cleaned_data["accessible_rooms"])

class AdminMemberForm(UpdatingUserFormMixin, MemberRoomForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Disable all fields if the member is marked for deletion
        if self.instance.marked_for_deletion:
            for field in self.fields:
                self.fields[field].disabled = True
            self.fields["marked_for_deletion"].disabled = False


# A form that allows a member to be updated or created
class MemberForm(UpdatingUserFormMixin, MemberRoomForm):
    class Meta:
        model = Member
        exclude = ("last_updated_by", "last_updated_date", "marked_for_deletion", "user", "notes", "is_deregistered")
        readonly_fields = ["accessible_rooms", "member_since", "is_honorary_member", "external_card_deposit", "key_id"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Disable fields marked as 'readonly' for clarity's sake
        #   Note that Django automagically ignores these fields as well
        #   in case they are tampered with by the client
        for field in self.Meta.readonly_fields:
            if field not in self.fields:
                raise ImproperlyConfigured("Field %s does not exist; form %s " % (field, self.__class__.__name__))
            self.fields[field].disabled = True

            # Also set a placeholder for uneditable fields to avoid
            #   confusion for uneditable empty values
            self.fields[field].widget.attrs["placeholder"] = "(None)"

    def is_valid(self):
        ret = super().is_valid()
        # Add an 'error' class to input elements that contain an error
        for field in self.errors:
            self.fields[field].widget.attrs.update(
                {"class": self.fields[field].widget.attrs.get("class", "") + " alert-danger"}
            )
        return ret


class ContinueMembershipForm(forms.Form):
    def __init__(self, *args, member=None, year=None, **kwargs):
        assert member is not None
        assert year is not None
        self.member = member
        self.year = year
        super(ContinueMembershipForm, self).__init__(*args, **kwargs)

    def clean(self):
        membership = Membership.objects.filter(year=self.year, member=self.member)
        if membership.exists():
            raise ValidationError(f"Member is already a member for {self.year}", code="already_member")
        return self.cleaned_data

    def save(self):
        Membership.objects.create(
            year=self.year,
            member=self.member,
        )

class RegisterMemberForm(UpdatingUserFormMixin, forms.ModelForm):
    """
    Registers a member in the membership file, and optionally sends them an email to link or register a Squire account.
    Also contains some useful presets.
    """
    class Meta:
        model = Member
        fields = ('first_name', 'tussenvoegsel', 'last_name', 'legal_name', 'student_number', 'educational_institution',
                  'tue_card_number', 'email', 'phone_number', 'street', 'house_number', 'house_number_addition', 'postal_code', 'city', 'country',
                  'date_of_birth', 'notes')

        widgets = {
            'educational_institution': OtherRadioSelect(choices=[
                ('TU/e', 'Eindhoven University of Technology'),
                ('Fontys Eindhoven', 'Fontys Eindhoven'),
                ('Summa College', 'Summa College'),
                ('', 'None (not a student)')
            ]),
            'city': OtherRadioSelect(choices=[('Eindhoven', 'Eindhoven'), ('Helmond', 'Helmond'), ('Veldhoven', 'Veldhoven')]),
            'country': OtherRadioSelect(choices=[('The Netherlands', 'The Netherlands'),]),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.has_active_years = False

        # Add field to automatically create memberships in one or more active years
        choices = [(year.id, year.name) for year in MemberYear.objects.filter(is_active=True)]

        if choices:
            # Skip the field entirely if there are no active years
            self.has_active_years = True
            field = forms.MultipleChoiceField(choices=choices, required=True, widget=forms.CheckboxSelectMultiple, initial=[choices[0][0]],
                label="Create membership for year(s)")
            self.fields["active_years"] = field

    def _save_m2m(self):
        """ Generate membership in active years """
        # This is done in _save_m2m as the member-instance must exist. This is only the case if commit=True
        super()._save_m2m()
        if self.has_active_years:
            # No need to do this if there were no active years to begin with
            years = MemberYear.objects.filter(id__in=self.cleaned_data['active_years'])

            for year in years:
                Membership.objects.create(member=self.instance, year=year, created_by=self.user)

