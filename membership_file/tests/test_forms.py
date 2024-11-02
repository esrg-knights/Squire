from django.core import mail
from django.http import HttpRequest
from django.test import TestCase
from unittest.mock import patch

from django.urls import reverse

from membership_file.forms import ContinueMembershipForm, RegisterMemberForm, ResendRegistrationForm
from membership_file.models import Member, MemberYear, Membership, Room
from membership_file.util import LinkAccountTokenGenerator
from utils.testing.form_test_util import FormValidityMixin


class ContinueMembershipFormTest(FormValidityMixin, TestCase):
    fixtures = ["test_users", "test_members"]
    form_class = ContinueMembershipForm

    def test_form_validity(self):
        # This already exists
        self.assertFormHasError(
            {},
            "already_member",
            member=Member.objects.get(id=1),
            year=MemberYear.objects.get(id=1),
        )
        self.assertFormValid(
            {},
            member=Member.objects.get(id=1),
            year=MemberYear.objects.get(id=3),
        )

    def test_saving(self):
        form = self.assertFormValid(
            {},
            member=Member.objects.get(id=1),
            year=MemberYear.objects.get(id=3),
        )
        form.save()
        self.assertTrue(Membership.objects.filter(member_id=1, year_id=3).exists())

    def test_form_kwarg_requirements(self):
        """Test that the required keyword arguments are checked (i.e. year and member may not be none)"""
        with self.assertRaises(AssertionError):
            self.build_form(
                {},
                member=Member.objects.get(id=1),
                year=MemberYear.objects.filter(id=999).first(),
            )
        with self.assertRaises(AssertionError):
            self.build_form(
                {},
                member=Member.objects.filter(id=999).first(),
                year=MemberYear.objects.get(id=1),
            )


@patch("django.http.request.HttpRequest.get_host", return_value="example.com")
class ResendRegistrationFormTestCase(FormValidityMixin, TestCase):
    """Tests for ResendRegistrationForm"""

    form_class = ResendRegistrationForm

    def get_form_kwargs(self, **kwargs):
        kwargs = super().get_form_kwargs(**kwargs)
        kwargs.update(request=HttpRequest(), token_generator=LinkAccountTokenGenerator())
        return kwargs

    def test_fields(self, _):
        """Tests the existence of fields"""
        # No fields should exist
        form = self.build_form({})
        self.assertDictEqual(form.fields, {})

    def test_save(self, _):
        """Tests saving"""
        self.assertFormValid({})


@patch("django.http.request.HttpRequest.get_host", return_value="example.com")
class RegisterMemberFormTestCase(FormValidityMixin, TestCase):
    """Tests for RegisterMemberForm"""

    form_class = RegisterMemberForm

    def get_form_kwargs(self, **kwargs):
        kwargs = super().get_form_kwargs(**kwargs)
        kwargs.update(request=HttpRequest(), token_generator=LinkAccountTokenGenerator())
        return kwargs

    def test_fields(self, _):
        """Tests the existence of conditional fields"""
        inactive = MemberYear.objects.create(is_active=False, name="2022")
        # No rooms/years active; no option to choose
        form = self.build_form({})
        self.assertNotIn("active_years", form.fields)
        self.assertNotIn("room_access", form.fields)
        fieldsets = form.get_fieldsets(HttpRequest(), None)
        self.assertNotIn("active_years", fieldsets)
        self.assertNotIn("room_access", fieldsets)

        # Years are active; default selection is most recent
        last_active = MemberYear.objects.create(is_active=True, name="2021")
        first_active = MemberYear.objects.create(is_active=True, name="2020")

        self.assertHasField(
            "active_years",
            required=True,
            initial=[last_active.id],
            choices=[(last_active.id, str(last_active)), (first_active.id, str(first_active))],
        )

        # Rooms become available once they exist
        kitchen = Room.objects.create(name="Kitchen", access_type=Room.ACCESS_OTHER, access_specification="Crowbar")
        self.assertHasField("room_access", required=False, initial=None, choices=[(kitchen.id, str(kitchen))])

        # Fieldsets should exist
        fieldsets = self.build_form({}).get_fieldsets(HttpRequest(), None)
        self.assertIn("active_years", fieldsets[-1][1]["fields"])
        self.assertIn("room_access", fieldsets[-1][1]["fields"])

    def test_clean(self, _):
        """Tests field cleaning"""
        # Phone number should be provided if room access is requested for rooms with keys,
        #   even if a tue card number is provided
        self.assertFormHasError(
            {
                "room_access": [
                    Room.objects.create(name="Kitchen", access_type=Room.ACCESS_OTHER).pk,
                    Room.objects.create(name="Basement", access_type=Room.ACCESS_CARD).pk,
                ],
                "tue_card_number": "01234567",
            },
            "phone_required",
            field_name="phone_number",
        )

        # If all requested rooms requires card access, and a tue card is provided, then no phone number is needed
        self.assertFormNotHasError(
            {
                "room_access": [Room.objects.create(name="Basement", access_type=Room.ACCESS_CARD).pk],
                "tue_card_number": "01234567",
            },
            "phone_required",
            field_name="phone_number",
        )

        # TU/e card is only relevant if studying at TU/e
        self.assertFormHasError(
            {"educational_institution": "Heiszwolf Military Academy", "tue_card_number": "123456"},
            "education_tue_required",
            field_name="tue_card_number",
        )

        # Student number is required when studying
        self.assertFormHasError(
            {"educational_institution": "Heiszwolf Military Academy"},
            "student_number_required",
            field_name="student_number",
        )

        # Except for PhD candidates
        self.assertFormNotHasError(
            {"educational_institution": "Heiszwolf Military Academy (PhD)"},
            "student_number_required",
            field_name="student_number",
        )

    def test_save(self, _):
        """Tests m2m saving"""
        data = {
            "first_name": "First",
            "tussenvoegsel": "",
            "last_name": "Last",
            "legal_name": "First Last",
            "student_number": "",
            "educational_institution": "",
            "tue_card_number": "",
            "email": "user@example.com",
            "phone_number": "+311234567890",
            "street": "Dorpsstraat",
            "house_number": "1",
            "house_number_addition": "",
            "postal_code": "1234 AB",
            "city": "Eindhoven",
            "country": "The Netherlands",
            "date_of_birth": "1970-01-01",
            "notes": "",
            "do_send_registration_email": False,
        }
        self.assertFormValid(data)

        # Room Access
        room = Room.objects.create(name="Kitchen", access_type=Room.ACCESS_OTHER, access_specification="Crowbar")
        data = {**data, "room_access": [room.pk]}
        form = self.build_form(data)
        self.assertFormValid(data)
        form.save()
        member = Member.objects.filter(email="user@example.com").first()
        self.assertTrue(member.accessible_rooms.filter(id=room.id).exists())
        member.delete()

        # Membership should be auto-created
        year = MemberYear.objects.create(is_active=True, name="2019")
        data = {**data, "active_years": [year.pk]}
        form = self.build_form(data)
        form.save()
        self.assertIsNotNone(Membership.objects.filter(member__email="user@example.com", year=year).first())

    def test_send_mail(self, _):
        """Tests mail sending functionality"""
        form: RegisterMemberForm = self.build_form({})
        subject = ("membership_file/registration/registration_subject.txt",)
        content = ("membership_file/registration/registration_email.txt",)
        html_content = "membership_file/testing/registration_email.html"
        form.send_mail(
            subject,
            content,
            {"uid": "uidb64", "token": "mytoken"},
            "from@example.com",
            "to@example.com",
            html_content,
            ["reply@example.com"],
        )

        self.assertEqual(len(mail.outbox), 1)
        registration_mail = mail.outbox[0]
        self.assertIn("Membership registered in Squire", registration_mail.subject)
        self.assertIn(reverse("membership:link_account/confirm", args=("uidb64", "mytoken")), registration_mail.body)
        self.assertEqual(registration_mail.from_email, "from@example.com")
        self.assertEqual(registration_mail.to, ["to@example.com"])
        self.assertEqual(registration_mail.reply_to, ["reply@example.com"])
        self.assertTrue(registration_mail.alternatives)
        body, alt = registration_mail.alternatives[0]
        self.assertEqual(body, "HTML EMAIL!")
        self.assertEqual(alt, "text/html")

        # No HTML
        mail.outbox = []
        form.send_mail(subject, content, {"uid": "uidb64", "token": "mytoken"}, "from@example.com", "to@example.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse(mail.outbox[0].alternatives)
