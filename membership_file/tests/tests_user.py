from django.test import TestCase, override_settings
from django import forms
from django.conf import settings
from django.core import serializers
from django.template import Context, Template

from core.tests.util import checkAccessPermissions, PermissionLevel
from membership_file.tests.util import checkAccessPermissionsMember, PermissionType
from membership_file.models import Member
from membership_file.models import MemberUser as User
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
    # Tests the field_label template tag
    def test_field_label(self):
        form_data = {
            'test_required_field': 'unused_filler_text',
            'test_optional_field': 'unused_filler_text',
        }
        form = DummyForm(data=form_data)

        # Test required field
        out = Template(
            "{% load field_label %}"
            "{% field_label 'MyFormFieldName' form.test_required_field %}"
        ).render(Context({
            'form': form,
        }))
        self.assertEqual(out, "MyFormFieldName*")

        # Test optional field
        out = Template(
            "{% load field_label %}"
            "{% field_label 'MyFormFieldName' form.test_optional_field %}"
        ).render(Context({
            'form': form,
        }))
        self.assertEqual(out, "MyFormFieldName")

################################################################
# VIEWS
################################################################

# Tests the editing feature of a user's own membership info.
@override_settings(MEMBERSHIP_FILE_EXPORT_PATH=None)
class MemberfileEditTest(TestCase):
    fixtures = ['test_users.json', 'test_members.json']

    def setUp(self):
        # Create a user
        self.user = User.objects.create(username="username", password="password")

        # Test Member Data
        self.member_data = {
            "initials": "J.D.",
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1970-01-01",
            "email": "johndoe@example.com",
            "street": "Main Street",
            "house_number": "42",
            "city": "New York",
            "country": "U.S.A.",
            "member_since": "1970-01-01",
            "educational_institution": "University of Toronto",
            "user": self.user,
        }
        # The member to test the request methods on
        self.member_to_run_tests_on = Member.objects.create(**self.member_data)

        # Save the models
        Member.save(self.member_to_run_tests_on)

    # Tests correct edit
    def test_correct_edit(self):
        form_data = {
            "initials": "J.D.",
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1970-01-01",
            "email": "johndoe@example.com",
            "street": "Main Street",
            "house_number": "69",
            "city": "New York",
            "country": "U.S.A.",
            "member_since": "1970-01-01",
            "educational_institution": "University of Toronto",
        }

        checkAccessPermissionsMember(self, '/account/membership/edit', 'post', PermissionType.TYPE_MEMBER,
                user=self.user, redirectUrl='/account/membership', data=form_data)
        
        member = Member.objects.filter(id=self.member_to_run_tests_on.id).first()
        self.assertIsNotNone(member)

        # Ensure the correct values were changed
        old_serialized_data = MemberSerializer(self.member_to_run_tests_on).data
        new_serialized_data = MemberSerializer(member).data
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
            "initials": "J.D.",
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1970-01-01",
            "email": "johndoe@example.com",
            "street": "Main Street",
            "house_number": "sixtynine", # House number should be a number
            "city": "New York",
            "country": "U.S.A.",
            "member_since": "1970-01-01",
            "educational_institution": "University of Toronto",
        }

        checkAccessPermissionsMember(self, '/account/membership/edit', 'post', PermissionType.TYPE_MEMBER,
                user=self.user, data=form_data)
        
        member = Member.objects.filter(id=self.member_to_run_tests_on.id).first()
        self.assertIsNotNone(member)

        # Ensure no values were changed
        old_serialized_data = MemberSerializer(self.member_to_run_tests_on).data
        new_serialized_data = MemberSerializer(member).data
        for field, value in old_serialized_data.items():
            # All other fields remain the same
            self.assertEqual(value, new_serialized_data[field], f"{field} did not match!")  

    # Tests if redirected if an unauthenticated user tries to edit information
    def test_unauthenticated_user_redirect(self):
        form_data = {
            "initials": "J.D.",
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1970-01-01",
            "email": "johndoe@example.com",
            "street": "Main Street",
            "house_number": "69",
            "city": "New York",
            "country": "U.S.A.",
            "member_since": "1970-01-01",
            "educational_institution": "University of Toronto",
        }

        checkAccessPermissionsMember(self, '/account/membership/edit', 'post', PermissionType.TYPE_NO_MEMBER,
                data=form_data, redirectUrl='/no_member')
        
        member = Member.objects.filter(id=self.member_to_run_tests_on.id).first()
        self.assertIsNotNone(member)

        # Ensure no values were changed
        old_serialized_data = MemberSerializer(self.member_to_run_tests_on).data
        new_serialized_data = MemberSerializer(member).data
        for field, value in old_serialized_data.items():
            # All other fields remain the same
            self.assertEqual(value, new_serialized_data[field], f"{field} did not match!")  

    # Tests if certain fields are properly ignored
    def test_ignore_fields(self):
        other_user = User.objects.create(username="user2", password="password")
        other_user.save()
        form_data = {
            "initials": "J.D.",
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1970-01-01",
            "email": "johndoe@example.com",
            "street": "Main Street",
            "house_number": "69",
            "city": "New York",
            "country": "U.S.A.",
            "member_since": "1970-01-01",
            "educational_institution": "University of Toronto",
            "user": other_user.id,
            "last_updated_by": "",
            "last_updated_date": "02/02/2002",
        }

        # Should still be redirected to the account page
        checkAccessPermissionsMember(self, '/account/membership/edit', 'post', PermissionType.TYPE_MEMBER,
                user=self.user, data=form_data, redirectUrl='/account/membership')

        member = Member.objects.filter(id=self.member_to_run_tests_on.id).first()
        self.assertIsNotNone(member)

        # Ensure the 'user' field is not edited
        self.assertEqual(self.member_to_run_tests_on.user, member.user)
        # Ensure the 'last updated by' and 'last updated date' fields are edited properly
        self.assertEqual(self.user, member.last_updated_by)
        self.assertTrue(self.member_to_run_tests_on.last_updated_date < member.last_updated_date)


# Tests views of the Membership info view/edit
class MemberfileViewTest(TestCase):
    fixtures = ['test_users.json', 'test_members.json']

    # Tests if the no-member page can be reached
    def test_no_member_page(self):
        checkAccessPermissions(self, '/no_member', 'get', PermissionLevel.LEVEL_PUBLIC)
        
    # Tests if members can view their info
    def test_member_view_info_page(self):
        checkAccessPermissionsMember(self, '/account/membership', 'get', PermissionType.TYPE_MEMBER)

    # Tests if non-members are redirected to the no_member page if they try to access the member info page
    def test_member_view_info_page_redirect(self):
        checkAccessPermissionsMember(self, '/account/membership', 'get', PermissionType.TYPE_NO_MEMBER, redirectUrl='/no_member')

    # Tests if members can access their edit info page
    def test_member_edit_info_page(self):
        checkAccessPermissionsMember(self, '/account/membership/edit', 'get', PermissionType.TYPE_MEMBER)

    # Tests if non-members are redirected to the no_member page if they try to access the member info edit page
    def test_member_edit_info_page_redirect(self):
        checkAccessPermissionsMember(self, '/account/membership/edit', 'get', PermissionType.TYPE_NO_MEMBER,
                redirectUrl='/no_member')


################################################################
# STRING FORMATTING
################################################################

# Tests several member-info-related formatting methods
@override_settings(MEMBERSHIP_FILE_EXPORT_PATH=None)
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
        # Display without state and house number addition
        self.member_to_run_tests_on.house_number_addition = None
        self.member_to_run_tests_on.state = None
        self.assertEqual("Main Street 42, New York, U.S.A.", self.member_to_run_tests_on.display_address())

        # Display with state and house number (alphabet character) addition
        self.member_to_run_tests_on.house_number_addition = "a"
        self.member_to_run_tests_on.state = "West Virginia"
        self.assertEqual("Main Street 42a, New York, West Virginia, U.S.A.", self.member_to_run_tests_on.display_address())

        # Display with state and house number (non-alphabet character) addition
        self.member_to_run_tests_on.house_number_addition = "0456"
        self.member_to_run_tests_on.state = "West Virginia"
        self.assertEqual("Main Street 42-0456, New York, West Virginia, U.S.A.", self.member_to_run_tests_on.display_address())

        # Display without state and with house number (alphabet character) addition
        self.member_to_run_tests_on.house_number_addition = "a"
        self.member_to_run_tests_on.state = None
        self.assertEqual("Main Street 42a, New York, U.S.A.", self.member_to_run_tests_on.display_address())

        # Display without state and with house number (non-alphabet character) addition
        self.member_to_run_tests_on.house_number_addition = "0456"
        self.member_to_run_tests_on.state = None
        self.assertEqual("Main Street 42-0456, New York, U.S.A.", self.member_to_run_tests_on.display_address())

        # Display with state and without house number addition
        self.member_to_run_tests_on.house_number_addition = None
        self.member_to_run_tests_on.state = "West Virginia"
        self.assertEqual("Main Street 42, New York, West Virginia, U.S.A.", self.member_to_run_tests_on.display_address())
