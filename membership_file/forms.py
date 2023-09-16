import copy
from typing import Any, Dict
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.mail import EmailMultiAlternatives, send_mail
from django.forms.models import ModelFormMetaclass
from django.http import HttpRequest
from django.template import loader
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _

from core.forms import LoginForm, RegisterForm
from membership_file.models import Member, Room, MemberYear, Membership
from membership_file.util import LinkAccountTokenGenerator
from utils.forms import UpdatingUserFormMixin
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


class FieldsetModelFormMetaclass(ModelFormMetaclass):
    """TODO"""

    def __new__(mcs, name, bases, attrs):
        new_class = super().__new__(mcs, name, bases, attrs)
        new_class._meta.fieldsets = None
        meta_class = getattr(new_class, "Meta", None)
        if meta_class is not None:
            new_class._meta.fieldsets = getattr(meta_class, "fieldsets", None)
        return new_class


class FieldsetAdminFormMixin(metaclass=FieldsetModelFormMetaclass):
    """TODO"""

    required_css_class = "required"

    # ModelAdmin media
    @property
    def media(self):
        extra = "" if settings.DEBUG else ".min"
        js = [
            "vendor/jquery/jquery%s.js" % extra,
            "jquery.init.js",
            "core.js",
            "admin/RelatedObjectLookups.js",
            "actions.js",
            "urlify.js",
            "prepopulate.js",
            "vendor/xregexp/xregexp%s.js" % extra,
        ]
        return forms.Media(js=["admin/js/%s" % url for url in js]) + super().media

    def get_fieldsets(self, request, obj=None):
        """
        Hook for specifying fieldsets.
        """
        if self._meta.fieldsets:
            return copy.deepcopy(self._meta.fieldsets)
        return [(None, {"fields": self.fields})]


class RegisterMemberForm(UpdatingUserFormMixin, FieldsetAdminFormMixin, forms.ModelForm):
    """
    Registers a member in the membership file, and optionally sends them an email to link or register a Squire account.
    Also contains some useful presets.
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
                        "send_registration_email",
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

    send_registration_email = forms.BooleanField(
        initial=True,
        required=False,
        help_text="Whether to email a registration link to the new member, allowing them to link their account to this membership data.",
    )

    def __init__(self, request: HttpRequest, token_generator: LinkAccountTokenGenerator, *args, **kwargs):
        self.domain = get_current_site(request).domain
        self.use_https = request.is_secure()
        self.token_generator = token_generator
        super().__init__(*args, **kwargs)

        # Make more fields required
        # TODO
        # req_fields = ('street', 'house_number', 'postal_code', 'city', 'country', 'date_of_birth')
        # for field in req_fields:
        #     self.fields[field].required = True

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
            self.add_error(
                "phone_number",
                ValidationError("A phone number is required if room access is provided.", code="phone_required"),
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
            # PhD'ers do not have student numbers
            if "(PhD)" not in self.cleaned_data["educational_institution"]:
                self.add_error(
                    "student_number",
                    ValidationError(
                        "A student number is required when an educational institution is set.",
                        code="student_number_required",
                    ),
                )

        return res

    def _save_m2m(self):
        """Auto-create related instances based on selections"""
        # This is done in _save_m2m as the member-instance must exist. This is only the case if commit=True
        super()._save_m2m()
        # Create membership in selected active years
        if self.cleaned_data["active_years"]:
            # No need to do this if there were no active years to begin with
            years = MemberYear.objects.filter(id__in=self.cleaned_data["active_years"])

            for year in years:
                # TODO: created_by must be a Member instance for some reason
                Membership.objects.create(member=self.instance, year=year)  # , created_by=self.user)

        # Room access
        if self.cleaned_data["room_access"]:
            self.instance.accessible_rooms.add(self.cleaned_data["room_access"])

        # Only send out an email once the member is actually saved
        if self.cleaned_data["send_registration_email"]:
            context = {
                "member": self.instance,
                "sender": {
                    "name": str(self.user),
                    "role": "Secretary",
                    "board_number": "305th board",
                    "board_name": "Het Ontbijtboard",
                },
                "domain": self.domain,
                "uid": urlsafe_base64_encode(force_bytes(self.instance.pk)),
                "token": self.token_generator.make_token(user=self.instance),
                "protocol": "https" if self.use_https else "http",
            }
            self.send_mail(
                "membership_file/registration/registration_subject.txt",
                "membership_file/registration/registration_email.txt",
                context,
                None,
                self.instance.email,
            )

    def send_mail(
        self, subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None
    ):
        """
        Send a django.core.mail.EmailMultiAlternatives to `to_email`.
        """
        # registration/registration_subject.txt
        # registration/registration_email.html

        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = "".join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)

        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name is not None:
            html_email = loader.render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, "text/html")

        email_message.send()


# TODO: RequestingUserMixin
class ConfirmLinkMembershipRegisterForm(RegisterForm):
    """TODO"""

    def __init__(self, member: Member, *args, **kwargs):
        # Member should not already have an attached user
        assert member.user is None
        print("form initialized")
        self.member = member
        super().__init__(*args, **kwargs)

    def _save_m2m(self):
        super()._save_m2m()
        print("save-m2m-called")
        # Attach new user to predetermined member
        self.member.user = self.instance
        print(self.member)
        print(self.instance)
        self.member.save()
