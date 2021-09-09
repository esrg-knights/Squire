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
    test_required_field = forms.CharField(required = True)
    test_optional_field = forms.CharField(required = False)

# Tests usage of custom template tags
class TemplateTagsTest(TestCase):
    # Tests the get_required_indicator filter
    def test_get_required_indicator(self):
        form_data = {
            'test_required_field': 'unused_filler_text',
            'test_optional_field': 'unused_filler_text',
        }
        form = DummyForm(data=form_data)

        # Test required field
        out = Template(
            "{% load field_tags %}"
            "{{ form.test_required_field|get_required_indicator }}"
        ).render(Context({
            'form': form,
        }))
        self.assertEqual(out, "*")

        # Test optional field
        out = Template(
            "{% load field_tags %}"
            "{{ form.test_optional_field|get_required_indicator }}"
        ).render(Context({
            'form': form,
        }))
        self.assertEqual(out, "")

################################################################
# VIEWS
################################################################

# Tests the editing feature of a user's own membership info.
class MemberfileEditTest(TestCase):
    fixtures = TestMemberUser.get_fixtures()

    def setUp(self):
        self.user = TestMemberUser.get_user_object()
        self.member = Member.objects.get(user=self.user)
        self.membership_permissions = [
            'membership_file.can_view_membership_information_self',
            'membership_file.can_change_membership_information_self',
        ]

        self.form_data = {
            "legal_name": self.member.legal_name,
            "first_name": self.member.first_name,
            "tussenvoegsel": self.member.tussenvoegsel,
            "last_name": self.member.last_name,
            "date_of_birth": self.member.date_of_birth,
            "email": self.member.email,
            "street": self.member.street,
            "house_number": self.member.house_number,
            "city": self.member.city,
            "country": self.member.country,
            "educational_institution": self.member.educational_institution,
            "student_number": self.member.student_number,
            "tue_card_number": self.member.tue_card_number,
        }

    # Tests correct edit
    def test_correct_edit(self):
        form_data = {
            **self.form_data,
            "house_number": "69",
        }

        check_http_response(self, '/account/membership/edit', 'post', TestMemberUser,
            permissions=self.membership_permissions,
            redirect_url='/account/membership', data=form_data)

        # The member must still exist
        updated_member = Member.objects.filter(id=self.member.id).first()
        self.assertIsNotNone(updated_member)

        # Ensure the correct values were changed
        old_serialized_data = MemberSerializer(self.member).data
        new_serialized_data = MemberSerializer(updated_member).data
        for field, value in old_serialized_data.items():
            if field == 'house_number':
                # House Number was updated
                self.assertEqual(69, new_serialized_data['house_number'])
            elif field == 'last_updated_date':
                # last_updated_date was updated
                self.assertTrue(value < new_serialized_data['last_updated_date'])
            elif field == 'last_updated_by':
                # last_updated_by was updated
                self.assertEqual(new_serialized_data['user'], self.user.id)
            else:
                # All other fields remain the same
                self.assertEqual(value, new_serialized_data[field], f"{field} did not match!")

    # Tests an invalid edit
    def test_invalid_edit(self):
        form_data = {
            **self.form_data,
            "house_number": "sixtynine", # House number should be a number
        }

        check_http_response(self, '/account/membership/edit', 'post', TestMemberUser,
            permissions=self.membership_permissions, data=form_data)

        # Member object should still exist
        updated_member = Member.objects.filter(id=self.member.id).first()
        self.assertIsNotNone(updated_member)

        # Ensure no values were changed
        old_serialized_data = MemberSerializer(self.member).data
        new_serialized_data = MemberSerializer(updated_member).data
        for field, value in old_serialized_data.items():
            # All fields remain the same
            self.assertEqual(value, new_serialized_data[field], f"{field} did not match!")

    # Tests if redirected if an unauthenticated user tries to edit information
    def test_unauthenticated_user_redirect(self):
        form_data = {
            "house_number": "69",
            **self.form_data,
        }

        check_http_response(self, '/account/membership/edit', 'post', TestAccountUser,
                permissions=self.membership_permissions, data=form_data, redirect_url=settings.MEMBERSHIP_FAIL_URL)

        # Member should still exist
        member = Member.objects.filter(id=self.member.id).first()
        self.assertIsNotNone(member)

        # Ensure no values were changed
        old_serialized_data = MemberSerializer(self.member).data
        new_serialized_data = MemberSerializer(member).data
        for field, value in old_serialized_data.items():
            # All other fields remain the same
            self.assertEqual(value, new_serialized_data[field], f"{field} did not match!")

    # Tests if certain fields are properly ignored
    def test_ignore_fields(self):
        other_user = User.objects.create(username="user2", password="password")
        form_data = {
            **self.form_data,
            "user": other_user.id,
            "last_updated_by": "",
            "last_updated_date": "02/02/2002",
        }

        # Should still be redirected to the account page
        check_http_response(self, '/account/membership/edit', 'post', TestMemberUser,
            permissions=self.membership_permissions, data=form_data, redirect_url='/account/membership')

        member = Member.objects.filter(id=self.member.id).first()
        self.assertIsNotNone(member)

        # Ensure the 'user' field is not edited
        self.assertEqual(self.member.user, member.user)
        # Ensure the 'last updated by' and 'last updated date' fields are edited properly
        self.assertEqual(self.user, member.last_updated_by)
        self.assertTrue(self.member.last_updated_date < member.last_updated_date)


# Tests views of the Membership info view/edit
class MemberfileViewTest(TestCase):
    fixtures = TestMemberUser.get_fixtures()

    # Tests if the no-member page can be reached
    def test_no_member_page(self):
        check_http_response(self, '/no_member', 'get', TestPublicUser)

    # Tests if members can view their info, and if non-members are redirected
    def test_member_view_info_page(self):
        check_http_response_with_member_redirect(self, '/account/membership', 'get', permissions=[
            'membership_file.can_view_membership_information_self',
            'membership_file.can_change_membership_information_self',
        ])

    # Tests if members can access their edit info page, and if non-members are redirected
    def test_member_edit_info_page(self):
        check_http_response_with_member_redirect(self, '/account/membership/edit', 'get', permissions=[
            'membership_file.can_view_membership_information_self',
            'membership_file.can_change_membership_information_self',
        ])


################################################################
# STRING FORMATTING
################################################################

# Tests several member-info-related formatting methods
class MemberRenderTest(TestCase):
    def setUp(self):
        # Create a user
        self.user = User.objects.create(username="username", password="password")

        # The member to test the display methods on
        self.member_to_run_tests_on = Member.objects.create(**{
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
        })

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
        self.member_to_run_tests_on.external_card_cluster = None
        self.assertIsNone(self.member_to_run_tests_on.display_external_card_number())

        # Display 1234567-123 if they exist
        self.member_to_run_tests_on.external_card_number = "1234567"
        self.member_to_run_tests_on.external_card_digits = "980"
        self.member_to_run_tests_on.external_card_cluster = None
        self.assertEqual("1234567-980", self.member_to_run_tests_on.display_external_card_number())

        # Display 1234567 (Cluster) if they exist
        self.member_to_run_tests_on.external_card_number = "1234567"
        self.member_to_run_tests_on.external_card_digits = None
        self.member_to_run_tests_on.external_card_cluster = "K. Nights"
        self.assertEqual("1234567 (K. Nights)", self.member_to_run_tests_on.display_external_card_number())

        # Display 1234567-980 (Cluster) if they exist
        self.member_to_run_tests_on.external_card_number = "1234567"
        self.member_to_run_tests_on.external_card_digits = "980"
        self.member_to_run_tests_on.external_card_cluster = "K. Nights"
        self.assertEqual("1234567-980 (K. Nights)", self.member_to_run_tests_on.display_external_card_number())

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
        self.assertEqual("Main Street 42-0456; 1395 AB, New York (U.S.A.)", self.member_to_run_tests_on.display_address())

        # Display nothing; no address provided
        self.member_to_run_tests_on.city = None
        self.assertIsNone(self.member_to_run_tests_on.display_address())
