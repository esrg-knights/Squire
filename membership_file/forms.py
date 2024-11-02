from typing import Any, Dict
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.mail import EmailMultiAlternatives
from django.http import HttpRequest
from django.template import loader
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from dynamic_preferences.registries import global_preferences_registry

from core.forms import LoginForm, RegisterForm
from membership_file.models import Member, Room, MemberYear, Membership
from membership_file.util import LinkAccountTokenGenerator
from utils.forms import FieldsetAdminFormMixin, UpdatingUserFormMixin
from utils.widgets import OtherRadioSelect

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


class RegistrationFormBase(forms.ModelForm):
    """Base class defining email functionality for sending registration emails to (new) members"""

    def __init__(self, request: HttpRequest, token_generator: LinkAccountTokenGenerator, *args, **kwargs):
        self.domain = get_current_site(request).domain
        self.use_https = request.is_secure()
        self.token_generator = token_generator
        super().__init__(*args, **kwargs)

    def send_registration_email(self):
        """Generates and sends a registration email"""
        # There is probably a better way to handle this than through a global preference,
        #   but it should do for now. This needs to be refactored anyway after #317 is merged.
        global_preferences = global_preferences_registry.manager()

        context = {
            "member": self.instance,
            "sender": {
                "name": str(self.user),
                "description": str(global_preferences["membership__registration_description"]),
                "extra_description": str(global_preferences["membership__registration_extra_description"]),
            },
            "domain": self.domain,
            "uid": urlsafe_base64_encode(force_bytes(self.instance.pk)),
            "token": self.token_generator.make_token(user=self.instance),
            "protocol": "https" if self.use_https else "http",
        }
        # Reply-To address
        reply_to = str(global_preferences["membership__registration_reply_to_address"]) or None
        if reply_to is not None:
            reply_to = reply_to.split(",")
        self.send_mail(
            "membership_file/registration/registration_subject.txt",
            "membership_file/registration/registration_email.txt",
            context,
            None,
            self.instance.email,
            reply_to=reply_to,
        )

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
        reply_to=None,
    ):
        """
        Send a django.core.mail.EmailMultiAlternatives to `to_email`.
        """

        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = "".join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)

        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email], reply_to=reply_to)
        if html_email_template_name is not None:
            html_email = loader.render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, "text/html")

        email_message.send()


class ResendRegistrationForm(UpdatingUserFormMixin, FieldsetAdminFormMixin, RegistrationFormBase):
    """
    Form that allows sending a registration email to a member.
    There's no fields here; we basically only want a submit button.
    """

    class Meta:
        model = Member
        fields = ()

    def save(self, commit=True) -> Any:
        # We don't call super().save(commit) because the object didn't actually change
        #   There's no need to activate signals or update auto_now fields
        self.send_registration_email()
        return self.instance


class RegisterMemberForm(UpdatingUserFormMixin, FieldsetAdminFormMixin, RegistrationFormBase):
    """
    Registers a member in the membership file, and optionally sends them an email to link or register a Squire account.
    Is able to automatically link an active year or room access. Also contains some useful presets, like those for
    educational institution.
    """

    class Meta:
        model = Member
        fields = (
            "first_name",
            "tussenvoegsel",
            "last_name",
            "legal_name",
            "student_number",
            "educational_institution",
            "tue_card_number",
            "email",
            "phone_number",
            "street",
            "house_number",
            "house_number_addition",
            "postal_code",
            "city",
            "country",
            "date_of_birth",
            "notes",
        )

        fieldsets = [
            (
                None,
                {
                    "fields": [
                        ("first_name", "tussenvoegsel", "last_name"),
                        "legal_name",
                        "date_of_birth",
                        ("educational_institution", "student_number"),
                        "tue_card_number",
                    ]
                },
            ),
            (
                "Contact Details",
                {
                    "fields": [
                        "email",
                        "do_send_registration_email",
                        "phone_number",
                        ("street", "house_number", "house_number_addition"),
                        ("postal_code", "city"),
                        "country",
                    ]
                },
            ),
            ("Miscellaneous", {"fields": ["notes"]}),
        ]

        widgets = {
            "educational_institution": OtherRadioSelect(
                choices=[
                    (Member.EDUCATIONAL_INSTITUTION_TUE, "Eindhoven University of Technology"),
                    (Member.EDUCATIONAL_INSTITUTION_TUE + " (PhD)", "TU/e (PhD)"),
                    ("Fontys Eindhoven", "Fontys Eindhoven"),
                    ("Summa College", "Summa College"),
                    ("", "None (not a student)"),
                ]
            ),
            "city": OtherRadioSelect(
                choices=[("Eindhoven", "Eindhoven"), ("Helmond", "Helmond"), ("Veldhoven", "Veldhoven")]
            ),
            "country": OtherRadioSelect(
                choices=[
                    ("The Netherlands", "The Netherlands"),
                ]
            ),
        }

    do_send_registration_email = forms.BooleanField(
        label="Send registration email?",
        initial=True,
        required=False,
        help_text="Whether to email a registration link to the new member, allowing them to link their account to this membership data.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make more fields required
        req_fields = ("street", "house_number", "postal_code", "city", "country", "date_of_birth")
        for field in req_fields:
            self.fields[field].required = True

        # Add field to automatically create memberships in one or more active years
        choices = [(year.id, year.name) for year in MemberYear.objects.filter(is_active=True)]
        if choices:
            # Skip the field entirely if there are no active years
            field = forms.MultipleChoiceField(
                choices=choices,
                required=True,
                widget=forms.CheckboxSelectMultiple,
                initial=[choices[0][0]],
                label="Create membership for year(s)",
            )
            self.fields["active_years"] = field

        # Add room access
        choices = [(room.id, str(room)) for room in Room.objects.all()]
        if choices:
            field = forms.MultipleChoiceField(
                choices=choices,
                required=False,
                widget=forms.CheckboxSelectMultiple,
                label="Grant access to room(s)",
                help_text="A phone number is required in order to gain access to a room.",
            )
            self.fields["room_access"] = field

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        # Append conditional fields to the last fieldset
        if "active_years" in self.fields:
            fieldsets[-1][1]["fields"].append("active_years")
        if "room_access" in self.fields:
            fieldsets[-1][1]["fields"].append("room_access")
        return fieldsets

    def clean(self) -> Dict[str, Any]:
        res = super().clean()
        # Phone number requirements
        if not self.cleaned_data["phone_number"] and self.cleaned_data["room_access"]:
            any_room_not_card = any(
                [
                    Room.objects.get(id=room_id).access_type != Room.ACCESS_CARD
                    for room_id in self.cleaned_data["room_access"]
                ]
            )
            # There is >=1 room that uses a key, or all rooms require card access and no TUe card number was provided
            if any_room_not_card or not self.cleaned_data["tue_card_number"]:
                msg = "A phone number is required; access was requested for rooms with keys."
                if not any_room_not_card:
                    msg = "A phone number is required, or a TUe card number should be entered. Access was only requested for rooms with card access."
                self.add_error(
                    "phone_number",
                    ValidationError(
                        msg,
                        code="phone_required",
                    ),
                )

        # Educational institution requirements
        if (
            self.cleaned_data["tue_card_number"]
            and self.cleaned_data["educational_institution"] != Member.EDUCATIONAL_INSTITUTION_TUE
        ):
            self.add_error(
                "tue_card_number",
                ValidationError(
                    "Member must study at the TU/e if a TU/e card number is entered.", code="education_tue_required"
                ),
            )

        if self.cleaned_data["educational_institution"] and not self.cleaned_data["student_number"]:
            # PhD candidates do not have student numbers
            if "(PhD)" not in self.cleaned_data["educational_institution"]:
                self.add_error(
                    "student_number",
                    ValidationError(
                        "A student number is required when an educational institution is set. For PhD candidates, set their educational institution to: <Educational Institution> (PhD)",
                        code="student_number_required",
                    ),
                )

        return res

    def _save_m2m(self):
        """Auto-create related instances based on selections"""
        # This is done in _save_m2m as the member-instance must exist. This is only the case if commit=True
        super()._save_m2m()
        # Create membership in selected active years
        if "active_years" in self.cleaned_data and self.cleaned_data["active_years"]:
            # No need to do this if there were no active years to begin with
            years = MemberYear.objects.filter(id__in=self.cleaned_data["active_years"])

            for year in years:
                # TODO: created_by must be a Member instance for some reason
                created_member = getattr(self.user, "member", None)
                Membership.objects.create(member=self.instance, year=year, created_by=created_member)

        # Room access
        if "room_access" in self.cleaned_data and self.cleaned_data["room_access"]:
            self.instance.accessible_rooms.add(*self.cleaned_data["room_access"])

        # Only send out an email once the member is actually saved
        if self.cleaned_data["do_send_registration_email"]:
            self.send_registration_email()


class ConfirmLinkMembershipRegisterForm(RegisterForm):
    """A RegisterForm that, when saved, also links a predetermined member to the newly registered user."""

    def __init__(self, member: Member, *args, **kwargs):
        # Member should not already have an attached user
        assert member.user is None
        self.member = member
        super().__init__(*args, **kwargs)

    def _save_m2m(self):
        super()._save_m2m()
        # Attach new user to predetermined member
        self.member.user = self.instance
        self.member.last_updated_by = self.instance
        self.member.save()


class ConfirmLinkMembershipLoginForm(LoginForm):
    """
    A LoginForm that, when saved, also links a predetermined member to the logged in user.
    Also sets the user's email and name to match that of the linked member.
    """

    def __init__(self, member: Member, *args, **kwargs):
        # Member should not already have an attached user
        assert member.user is None
        self.member = member
        super().__init__(*args, **kwargs)

    def save(self):
        # Attach new user to predetermined member
        user = self.get_user()
        self.member.user = user
        self.member.last_updated_by = user
        self.member.save()

        # Update user email and real name
        user.email = self.member.email
        user.first_name = self.member.get_full_name(allow_spoof=False)
        user.save()
