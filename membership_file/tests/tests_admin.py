from django.contrib.admin import ModelAdmin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.test.client import RequestFactory

from core.tests.util import suppress_warnings
from membership_file.admin import MemberWithLog, reset_has_paid_membership_fee
from membership_file.tests.util import fillDictKeys
from membership_file.models import Member, MemberLog, MemberLogField


##################################################################################
# Test cases for MemberLog-logic and Member deletion logic on the admin-side
# @since 19 JUL 2019
##################################################################################

class MemberAdminTest(TestCase):
    """ Testcases for MemberWithLog """
    fixtures = ['test_users.json', 'test_members.json']

    def setUp(self):
        self.model_admin = MemberWithLog(model=Member, admin_site=AdminSite())
        self.user = User.objects.all().first()

        factory = RequestFactory()
        self.request = factory.get('/testurl/')
        self.request.user = self.user

    def test_bulk_reset_membership_fee(self):
        """ Tests if the bulk resetting membership fee admin action updates
        has_paid_membership_fee and created logs (if needed) """
        Member.objects.all().update(has_paid_membership_fee=True, last_updated_by=None)
        # Already reset
        member = Member.objects.get(id=1)
        member.has_paid_membership_fee = False
        member.save()

        # Get rid of all the logs
        MemberLog.objects.all().delete()

        # Exclude a single member
        queryset = Member.objects.exclude(id=2)
        reset_has_paid_membership_fee(self.model_admin, self.request, queryset)

        for member in Member.objects.all():
            if member.id == 1:
                # Already reset
                self.assertIsNone(member.last_updated_by)
                self.assertFalse(member.has_paid_membership_fee)
                self.assertIsNone(member.memberlog_set.all().first())

            elif member.id == 2:
                # Not part of the queryset
                self.assertIsNone(member.last_updated_by)
                self.assertTrue(member.has_paid_membership_fee)
                self.assertIsNone(member.memberlog_set.all().first())
            else:
                # Updated
                self.assertEqual(member.last_updated_by, self.user)
                self.assertFalse(member.has_paid_membership_fee)
                memberlogs = member.memberlog_set.all()
                self.assertEqual(len(memberlogs), 1)
                self.assertEqual(memberlogs.first().updated_fields.first().field, "has_paid_membership_fee")


# Tests Log deletion when members are deleted
class MemberLogCleanupTest(TestCase):
    def setUp(self):
        # Called each time before a testcase runs
        # Set up data for each test.
        # Objects are refreshed here and a client (to make HTTP-requests) is created here
        self.client = Client()

        # Create a Member
        self.memberData = {
            "first_name": "Luna",
            "last_name": "Fest",
            "date_of_birth": "1970-01-01",
            "email": "lunafest@example.com",
            "street": "De Lampendriessen",
            "house_number": "31",
            "city": "Eindhoven",
            "country": "The Netherlands",
            "member_since": "1970-01-01",
            "educational_institution": "TU/e",
            "legal_name": "Lunafest",
        }
        self.member = Member.objects.create(**self.memberData)

        # Save the models
        Member.save(self.member)

    # Tests if an INSERT MemberLog is created after creating a new member
    # but without marked_for_deletion
    def test_delete_member(self):
        self.member.delete()

        # No memberlog or memberlogfields should exist after deleting the member
        self.assertIsNone(MemberLog.objects.all().first())
        self.assertIsNone(MemberLogField.objects.all().first())

    def test_delete_member_logs(self):
        memberLog = MemberLog.objects.all().first()
        self.assertIsNotNone(memberLog)

        memberLog.delete()

        # No memberlog or memberlogfields should exist after deleting the memberlog
        self.assertIsNone(MemberLog.objects.all().first())
        self.assertIsNone(MemberLogField.objects.all().first())

# Tests Log creation when updating members
class MemberLogTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Called once at the beginning of the test setup
        # Set up data for the whole TestCase

        # An empty dictionary of all fields that are set when making a POST request for a member
        cls.emptyMemberDictionary = {
            "memberlog_set-TOTAL_FORMS": 0,
            "memberlog_set-INITIAL_FORMS": 0,
            "memberlog_set-MIN_NUM_FORMS": 0,
            "memberlog_set-MAX_NUM_FORMS": 0,
        }

    def setUp(self):
        # Called each time before a testcase runs
        # Set up data for each test.
        # Objects are refreshed here and a client (to make HTTP-requests) is created here
        self.client = Client()

        # Create normal user and admin here
        self.user = User.objects.create(username="username", password="password")
        self.user2 = User.objects.create(username="username2", password="password")
        self.admin = User.objects.create_superuser(username="admin", password="admin", email="")

        # Create a Member
        self.memberData = {
            "legal_name": "F.C.",
            "first_name": "Fantasy",
            "last_name": "Court",
            "date_of_birth": "1970-01-01",
            "email": "info@example.com",
            "street": "Veld",
            "house_number": "5",
            "city": "Eindhoven",
            "country": "The Netherlands",
            "member_since": "1970-01-01",
            "educational_institution": "TU/e",
        }
        self.member = Member.objects.create(**self.memberData)
        self.memberData = fillDictKeys(self.emptyMemberDictionary, self.memberData)

        # Save the models
        User.save(self.user)
        User.save(self.user2)
        User.save(self.admin)
        Member.save(self.member)

        # Remove member logs related to self.member
        MemberLog.objects.all().delete()

        # Define test data
        self.email = "info-kotkt@example.com"
        self.data = {
            "legal_name": "E.S.R.G.",
            "first_name": "Knights",
            "tussenvoegsel": "of the",
            "last_name": "Kitchen Table",
            "student_number": "",
            "educational_institution": "TU/e",
            "external_card_digits": "",
            "external_card_cluster": "",
            "email": self.email,
            "street": "De Lampendriessen",
            "house_number": "31",
            "house_number_addition": "11",
            "postal_code": "1228 AB",
            "city": "Eindhoven",
            "country": "The Netherlands",
            "date_of_birth": "1970-01-01",
            "member_since": "1970-01-01",
            "is_deregistered": True,
            "is_honorary_member": False,
            "has_paid_membership_fee": False,
            "notes": "",
        }
        self.numNonEmptyFields = len(self.data)
        self.data = fillDictKeys(self.emptyMemberDictionary, self.data)

    # Tests if an INSERT MemberLog is created after creating a new member
    # but without marked_for_deletion
    def test_create_memberlog_insert(self):
        # Ensure the admin is logged in
        self.client.force_login(self.admin)

        # Issue a POST request.
        response = self.client.post('/admin/membership_file/member/add/', data=self.data, follow=True)

        # Ensure that the request is correctly handled
        self.assertEqual(response.status_code, 200)

        # Check if the member and its associated logs got added correctly
        member_got_correctly_added(self)

        # Only 1 log should exist
        self.assertEqual(1, MemberLog.objects.all().count())


    # Tests if an INSERT MemberLog is created after creating a new member
    # Should also create a DELETE MemberLog afterwards
    def test_create_memberlog_insert_marked_for_deletion(self):
        # Ensure the admin is logged in
        self.client.force_login(self.admin)

        # Newly created member was immediately marked for deletion
        self.data['marked_for_deletion'] = 'on'

        # Issue a POST request.
        response = self.client.post('/admin/membership_file/member/add/', data=self.data, follow=True)

        # Ensure that the request is correctly handled
        self.assertEqual(response.status_code, 200)

        # Check if the member and its associated logs got added correctly
        insertLog = member_got_correctly_added(self)
        member = insertLog.member

        # Ensure that a DELETE-MemberLog was also created
        deleteLog = MemberLog.objects.filter(
            user__id = self.admin.id,
            member__id = member.id,
            log_type = "DELETE",
        ).first()
        self.assertIsNotNone(deleteLog)

        # Only 2 logs should exist
        self.assertEqual(2, MemberLog.objects.all().count())

        # A DELETE-log does not have fields
        self.assertIsNone(MemberLogField.objects.filter(member_log__id = deleteLog.id).first())

        # The DELETE-log should be created later than the INSERT-log
        self.assertGreater(deleteLog.id, insertLog.id)

    # Tests if a DELETE MemberLog is created when setting marked_for_deletion = True
    def test_set_marked_for_deletion(self):
        # Ensure the admin is logged in
        self.client.force_login(self.admin)

        # The member got marked for deletion
        self.memberData['marked_for_deletion'] = 'on'

        # Issue a POST request.
        response = self.client.post('/admin/membership_file/member/' + str(self.member.id) + '/change/', data=self.memberData, follow=True)

        # Ensure that the request is correctly handled
        self.assertEqual(response.status_code, 200)

        # Ensure that a DELETE-MemberLog was also created
        deleteLog = MemberLog.objects.filter(
            user__id = self.admin.id,
            member__id = self.member.id,
            log_type = "DELETE",
        ).first()
        self.assertIsNotNone(deleteLog)

        # No other logs should exist
        self.assertEqual(1, MemberLog.objects.count())

        # No MemberLogFields should exist
        self.assertIsNone(MemberLogField.objects.filter().first())


    # Tests if an UPDATE MemberLog is created after updating a member
    # but without marked_for_deletion
    def test_create_memberlog_update(self):
        # Ensure the admin is logged in
        self.client.force_login(self.admin)

        # The member's data got updated
        updatedFields = {
            'first_name': 'NewFirstName',
            'email': 'newemail@example.com',
        }
        self.memberData = {**self.memberData, **updatedFields}

        # Issue a POST request.
        response = self.client.post('/admin/membership_file/member/' + str(self.member.id) + '/change/', data=self.memberData, follow=True)

        # Ensure that the request is correctly handled
        self.assertEqual(response.status_code, 200)

        # Check if the member and its associated logs got added correctly
        member_got_correctly_updated(self, updatedFields)

        # Only 1 log should exist
        self.assertEqual(1, MemberLog.objects.all().count())


    # Tests if an UPDATE MemberLog is created after updating a member
    # Should also create a DELETE MemberLog afterwards
    def test_create_memberlog_update_marked_for_deletion(self):
        # Ensure the admin is logged in
        self.client.force_login(self.admin)

        # The member's data got updated
        updatedFields = {
            'first_name': 'NewFirstName',
            'email': 'newemail@example.com',
            'marked_for_deletion': 'on',
        }
        self.memberData = {**self.memberData, **updatedFields}

        # Issue a POST request.
        response = self.client.post('/admin/membership_file/member/' + str(self.member.id) + '/change/', data=self.memberData, follow=True)

        # Ensure that the request is correctly handled
        self.assertEqual(response.status_code, 200)

        # Check if the member and its associated logs got added correctly
        updateLog = member_got_correctly_updated(self, updatedFields)

        # Ensure that a DELETE-MemberLog was also created
        deleteLog = MemberLog.objects.filter(
            user__id = self.admin.id,
            member__id = self.member.id,
            log_type = "DELETE",
        ).first()
        self.assertIsNotNone(deleteLog)

        # Only 2 logs should exist
        self.assertEqual(2, MemberLog.objects.all().count())

        # A DELETE-log does not have fields
        self.assertIsNone(MemberLogField.objects.filter(member_log__id = deleteLog.id).first())

        # The DELETE-log should be created later than the UPDATE-log
        self.assertGreater(deleteLog.id, updateLog.id)

# Checks if a member got correctly added and if the correct logs were created
# @param self An instance of the MemberLogTest-class
# @pre self != None
# @returns The Insertlog that was created
def member_got_correctly_added(self: MemberLogTest) -> MemberLog:
    # The newly created member must exist in the Database
    member = Member.objects.filter(email=self.email).first()
    self.assertIsNotNone(member)

    # ID-field was created in the process
    self.data['id'] = str(member.id)

    # There must exist an INSERT-MemberLog for this member
    memberLogs = MemberLog.objects.filter(
        user__id = self.admin.id,
        member__id = member.id,
        log_type = "INSERT"
    )
    # There must exist exactly 1 INSERT-memberlog
    self.assertEqual(1, memberLogs.count())
    memberLog = memberLogs.first()

    # There must exist MemberLogFields for the newly created member
    for key in self.data:
        # MemberLogField only exists if non-empty data was passed
        if self.data[key]:
            self.assertIsNotNone(MemberLogField.objects.filter(
                member_log__id = memberLog.id,
                field = key,
                old_value = None,
                new_value = self.data[key],
            ))

    # No other MemberLogFields got added (except the ID-field)
    self.assertEqual(self.numNonEmptyFields + 1, MemberLogField.objects.filter().count())

    return memberLog


# Checks if a member got correctly updated and if the correct logs were created
# @param self An instance of the MemberLogTest-class
# @param updatedFields The fields that were updated
# @pre self != None
# @returns The UPDATE-log that was created
def member_got_correctly_updated(self: MemberLogTest, updatedFields: dict) -> MemberLog:
    # There must exist an UPDATE-MemberLog for this member
    memberLogs = MemberLog.objects.filter(
        user__id = self.admin.id,
        member__id = self.member.id,
        log_type = "UPDATE"
    )
    # There must exist exactly 1 UPDATE-memberlog
    self.assertEqual(1, memberLogs.count())
    memberLog = memberLogs.first()

    # There must exist MemberLogFields for the newly created member
    for key in updatedFields:
        # MemberLogField only exists if non-empty data was passed
        if updatedFields[key]:
            self.assertIsNotNone(MemberLogField.objects.filter(
                member_log__id = memberLog.id,
                field = key,
                old_value = None,
                new_value = updatedFields[key],
            ))

    # No other MemberLogFields got added
    numLogs = len(updatedFields) - (1 if updatedFields.get('marked_for_deletion') else 0)
    self.assertEqual(numLogs, MemberLogField.objects.filter().count())

    return memberLog


# Tests Deletion logic for Members
class DeleteMemberTest(TestCase):
    @classmethod
    def setUpTestData(self):
        self.modelAdmin = ModelAdmin(model=Member, admin_site=AdminSite())

    def setUp(self):
        # Called each time before a testcase runs
        # Set up data for each test.
        # Objects are refreshed here and a client (to make HTTP-requests) is created here
        self.client = Client()

        # Create normal user and admin here
        self.admin = User.objects.create_superuser(username="admin", password="admin", email="")
        self.admin2 = User.objects.create_superuser(username="admin2", password="admin", email="")

        # Create a Member
        self.memberData = {
            "first_name": "HTTPs",
            "last_name": "Committee",
            "date_of_birth": "1970-01-01",
            "email": "https@example.com",
            "street": "Veld",
            "house_number": "5",
            "city": "Eindhoven",
            "country": "The Netherlands",
            "member_since": "1970-01-01",
            "educational_institution": "TU/e",
            "legal_name": "Hackmanite Turbotyping Programming Squad",
        }
        self.member = Member.objects.create(**self.memberData)

        self.memberData = {
            "memberlog_set-TOTAL_FORMS": 0,
            "memberlog_set-INITIAL_FORMS": 0,
            "memberlog_set-MIN_NUM_FORMS": 0,
            "memberlog_set-MAX_NUM_FORMS": 0,
            **self.memberData,
        }

        # Save the models
        User.save(self.admin)
        User.save(self.admin2)
        Member.save(self.member)

    # Tests if a member cannot be deleted if it is NOT marked for deletion
    @suppress_warnings
    def test_delete_member_not_marked_for_deletion(self):
        # Ensure the admin is logged in
        self.client.force_login(self.admin)

        # Issue a POST request.
        response = self.client.post('/admin/membership_file/member/' + str(self.member.id) + '/delete/', data={"post": "yes"}, follow=True)

        # Ensure that the a 403 Forbidden response is issued
        self.assertEqual(response.status_code, 403)

        # The member should not be deleted
        self.assertEqual(1, Member.objects.all().count())



    # Tests if a member cannot be deleted by the user that marked it for deletion
    @suppress_warnings
    def test_delete_member_marked_for_deletion_by_same_user(self):
        # Ensure the admin is logged in
        self.client.force_login(self.admin)

        # Set the member marked to be deleted
        self.member.marked_for_deletion = True
        self.member.last_updated_by = self.admin

        Member.save(self.member)

        # Issue a POST request.
        response = self.client.post('/admin/membership_file/member/' + str(self.member.id) + '/delete/', data={"post": "yes"}, follow=True)

        # Ensure that a 403 Forbidden response is issued
        self.assertEqual(response.status_code, 403)

        # The member should not be deleted
        self.assertEqual(1, Member.objects.all().count())

    # Tests if a member can be deleted if it was marked for deletion by another user
    def test_delete_member_allowed(self):
        # Ensure the admin is logged in
        self.client.force_login(self.admin)

        # Set the member marked to be deleted
        self.member.marked_for_deletion = True
        self.member.last_updated_by = self.admin2

        Member.save(self.member)

        # Issue a POST request.
        response = self.client.post('/admin/membership_file/member/' + str(self.member.id) + '/delete/', data={"post": "yes"}, follow=True)

        # Ensure that the request is correctly handled
        self.assertEqual(response.status_code, 200)

        # The member should be deleted
        self.assertEqual(0, Member.objects.all().count())

    # Tests if a member cannot have its information updated if it is marked for deletion
    def test_update_member_when_marked_for_deletion(self):
        # Ensure the admin is logged in
        self.client.force_login(self.admin)

        # Set the member marked to be deleted
        self.member.marked_for_deletion = True
        self.member.last_updated_by = self.admin2
        self.memberData['marked_for_deletion'] = 'on'

        self.member.save()

        # Remove MemberLogs that were created during this update
        MemberLog.objects.all().delete()

        # Try to update this member's, even though marked_for_deletion = True
        updatedFields = {
            'first_name': 'NewFirstName',
        }
        postData = {**self.memberData, **updatedFields}

        # Issue a POST request.
        response = self.client.post('/admin/membership_file/member/' + str(self.member.id) + '/change/', data=postData, follow=True)

        # Ensure that the readonly_fields are ignored
        self.assertEqual(response.status_code, 200)

        # Ensure that the name of the member was unchanged
        self.assertEqual(Member.objects.get(id=self.member.id).first_name, self.memberData['first_name'])

        # Ensure that no memberlog got created
        self.assertEqual(MemberLog.objects.all().count(), 0)
