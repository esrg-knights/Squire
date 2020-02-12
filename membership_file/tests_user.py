from django.test import TestCase
from django.contrib.auth.models import User
from django import forms
from django.template import Context, Template
from enum import Enum

from .models import Member
from core.tests import checkAccessPermissions, PermissionLevel

##################################################################################
# Test cases for MemberLog-logic and Member deletion logic on the user-side
# @author E.M.A. Arts
# @since 12 FEB 2020
##################################################################################

class PermissionType(Enum):
    TYPE_MEMBER = 1
    TYPE_NO_MEMBER = 2

def checkAccessPermissionsMember(test: TestCase, url: str, httpMethod: str, permissionType: PermissionType,
        user: User = None, redirectUrl: str = "", data: dict = {}) -> None:
    
    # Create a user if it does not exist
    if user is None:
        user = User.objects.create_user(username="username", password="username")
    User.save(user)

    # Make the user a member
    member = None
    linked_members = Member.objects.filter(user=user)
    if permissionType == PermissionType.TYPE_MEMBER:
        if not linked_members.exists():
            # User should be linked to a member, but this was not yet the case
            member = Member.objects.create(**{
                "user": user,
                "initials": "H.T.T.P.S.",
                "first_name": "Hackmanite",
                "last_name": "Turbo",
                "date_of_birth": "1970-01-02",
                "email": "https@kotkt.nl",
                "street": "Port",
                "house_number": "418",
                "city": "The Internet",
                "country": "The Netherlands",
                "member_since": "1970-01-01",
                "educational_institution": "Python",
            })
            Member.save(member)
            member.user = user
            User.save(user)
    elif linked_members.exists():
        # User should NOT be linked to a member, but this was the case
        linked_members.update(user=None)
        for linked_member in linked_members:
            linked_member.user = None
            linked_member.save()

    checkAccessPermissions(test, url, httpMethod, PermissionLevel.LEVEL_USER, user, redirectUrl, data)


class DummyForm(forms.Form): 
    test_required_field = forms.CharField(required = True) 
    test_optional_field = forms.CharField(required = False)

# Tests Log deletion when members are deleted
class TemplateTagsTest(TestCase):
    def setUp(self):
        pass

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

# Tests views of the Membership info view/edit
class MemberfileViewTest(TestCase):
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

    # TODO: POST-request for edit info

class MemberRenderTest(TestCase):
    def setUp(self):
        # Create a user
        self.user = User.objects.create(username="username", password="password")

        # The member to test the display methods on
        self.member_to_run_tests_on = Member.objects.create(**{
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1970-01-01",
            "email": "johndoe@gmail.com",
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
            "email": "de-bunker@de-bunker.nl",
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
