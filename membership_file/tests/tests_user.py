from django.test import TestCase
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.template import Context, Template

from core.tests.util import TestAccountUser, check_http_response, TestPublicUser
from membership_file.tests.util import TestMemberUser, check_http_response_with_member_redirect
from membership_file.models import Member
from membership_file.serializers import MemberSerializer

##################################################################################
# Test cases for MemberLog-logic and Member deletion logic on the user-side
# @since 12 FEB 2020
##################################################################################


################################################################
# TEMPLATE TAGS
################################################################
# Dummy form used during test cases
class DummyForm(forms.Form):
    test_required_field = forms.CharField(required=True)
    test_optional_field = forms.CharField(required=False)


# Tests usage of custom template tags
class TemplateTagsTest(TestCase):
    # Tests the get_required_indicator filter
    def test_get_required_indicator(self):
        form_data = {
            "test_required_field": "unused_filler_text",
            "test_optional_field": "unused_filler_text",
        }
        form = DummyForm(data=form_data)

        # Test required field
        out = Template("{% load field_tags %}" "{{ form.test_required_field|get_required_indicator }}").render(
            Context(
                {
                    "form": form,
                }
            )
        )
        self.assertEqual(out, "*")

        # Test optional field
        out = Template("{% load field_tags %}" "{{ form.test_optional_field|get_required_indicator }}").render(
            Context(
                {
                    "form": form,
                }
            )
        )
        self.assertEqual(out, "")


################################################################
# STRING FORMATTING
################################################################


# Tests several member-info-related formatting methods
class MemberRenderTest(TestCase):
    def setUp(self):
        # Create a user
        self.user = User.objects.create(username="username", password="password")

        # The member to test the display methods on
        self.member_to_run_tests_on = Member.objects.create(
            **{
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1970-01-01",
                "email": "johndoe@example.com",
                "street": "Main Street",
                "house_number": "42",
                "postal_code": "1395 AB",
                "city": "New York",
                "country": "U.S.A.",
                "member_since": "1970-01-01",
                "educational_institution": "University of Toronto",
                "user": self.user,
            }
        )

        # Save the models
        Member.save(self.member_to_run_tests_on)

    # Tests the last updated name display method
    def test_last_updated_name(self):
        # Create a Member
        memberData = {
            "first_name": "De",
            "last_name": "Bunker",
            "date_of_birth": "1970-01-01",
            "email": "de-bunker@example.com",
            "street": "John F. Kennedylaan",
            "house_number": "3",
            "city": "Eindhoven",
            "country": "The Netherlands",
            "member_since": "1970-01-01",
            "educational_institution": "TU/e",
            "legal_name": "De Bunker",
        }
        updater_member = Member.objects.create(**memberData)
        updater = User.objects.create_user(username="updater_username", password="password")

        # Display None if no-one updated
        self.assertIsNone(self.member_to_run_tests_on.display_last_updated_name())

        # Display username if the updater is not a member
        self.member_to_run_tests_on.last_updated_by = updater
        self.assertEqual("updater_username", self.member_to_run_tests_on.display_last_updated_name())

        # Display name if the updater is a member
        updater_member.user = updater
        updater_member.save()
        self.assertEqual("De Bunker", self.member_to_run_tests_on.display_last_updated_name())

        # Display 'You' if the user updated itself
        self.member_to_run_tests_on.last_updated_by = self.user
        self.assertEqual("You", self.member_to_run_tests_on.display_last_updated_name())

    # Tests the external card number display method
    def test_external_card_number(self):
        # Display None if there is no card number
        self.member_to_run_tests_on.external_card_number = None
        self.member_to_run_tests_on.external_card_digits = None
        self.assertIsNone(self.member_to_run_tests_on.display_external_card_number())

        # Display 1234567-123 if they exist
        self.member_to_run_tests_on.external_card_number = "1234567"
        self.member_to_run_tests_on.external_card_digits = "980"
        self.assertEqual("1234567-980", self.member_to_run_tests_on.display_external_card_number())

        # Display 1234567 if they exist
        self.member_to_run_tests_on.external_card_number = "1234567"
        self.member_to_run_tests_on.external_card_digits = None
        self.assertEqual("1234567", self.member_to_run_tests_on.display_external_card_number())

    # Tests the address display method
    def test_address(self):
        # Display without house number addition
        self.member_to_run_tests_on.house_number_addition = None
        self.assertEqual("Main Street 42; 1395 AB, New York (U.S.A.)", self.member_to_run_tests_on.display_address())

        # Display with house number (alphabet character) addition
        self.member_to_run_tests_on.house_number_addition = "a"
        self.assertEqual("Main Street 42a; 1395 AB, New York (U.S.A.)", self.member_to_run_tests_on.display_address())

        # Display with house number (non-alphabet character) addition
        self.member_to_run_tests_on.house_number_addition = "0456"
        self.assertEqual(
            "Main Street 42-0456; 1395 AB, New York (U.S.A.)", self.member_to_run_tests_on.display_address()
        )

        # Display nothing; no address provided
        self.member_to_run_tests_on.city = None
        self.assertIsNone(self.member_to_run_tests_on.display_address())
