from django.test import TestCase
from django.test import Client
from .models import Member, MemberLog, MemberLogField
from django.contrib.auth.models import User
from .serializers import MemberSerializer

##################################################################################
# Test cases for MemberLog-logic and Member deletion logic
# @author E.M.A. Arts
# @since 19 JUL 2019
##################################################################################

# Fills the keys of one dictionary with those of another
# @param toFill The dictionary to fill
# @param fillData The dictionary whose data to use to fill empty
# @returns The values from fillData are in toFill
def fillDictKeys(toFill: dict, fillData: dict) -> dict:
    return {**toFill, **fillData}

# Gets the number of non-empty fields in a dictionary
# @param data The dictionary
# @returns the number of non-empty fields in a dictionary
def getNumNonEmptyFields(data: dict) -> int:
    count = 0
    for key in data:
        if data[key]:
            count += 1
    return count

class MemberUpdateTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Called once at the beginning of the test setup
        # Set up data for the whole TestCase

        # An empty dictionary of all fields that are set when making a POST request for a member
        cls.emptyMemberDictionary = {
            "user": "",
            "first_name": "",
            "tussenvoegsel": "",
            "last_name": "",
            "tue_card_number": "",
            "external_card_number": "",
            "external_card_cluster": "",
            "date_of_birth": "",
            "email": "",
            "phone_number": "",
            "street": "",
            "house_number": "",
            "house_number_addition": "",
            "city": "",
            "state": "",
            "country": "",
            "postal_code": "",
            "member_since": "",
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
            "first_name": "Fantasy",
            "last_name": "Court",
            "date_of_birth": "1970-01-01",
            "email": "info@fantasycourt.nl",
            "street": "Veld",
            "house_number": "5",
            "city": "Eindhoven",
            "country": "The Netherlands",
            "postal_code": "5612 AH",
            "member_since": "1970-01-01",
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
        self.email = "info@kotkt.nl"
        self.data = fillDictKeys(self.emptyMemberDictionary, {
            "user": "",
            "first_name": "Knights",
            "tussenvoegsel": "of the",
            "last_name": "Kitchen Table",
            "date_of_birth": "1970-01-01",
            "email": self.email,
            "street": "De Lampendriessen",
            "house_number": "31",
            "house_number_addition": "11",
            "city": "Eindhoven",
            "state": "Noord-Brabant",
            "country": "The Netherlands",
            "postal_code": "5612 AH",
            "member_since": "1970-01-01",
        })
        self.numNonEmptyFields = getNumNonEmptyFields(self.data)

    # Tests if an INSERT MemberLog is created after creating a new member
    # but without marked_for_deletion
    def test_create_memberlog_insert(self):
        # Ensure the admin is logged in
        self.client.force_login(self.admin)

        # Issue a POST request.
        response = self.client.post('/admin/membership_file/member/add/', data=self.data)

        # Ensure that no internal server error occurs
        self.assertNotEqual(response.status_code, 500)

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
        response = self.client.post('/admin/membership_file/member/add/', data=self.data)

        # Ensure that no internal server error occurs
        self.assertNotEqual(response.status_code, 500)

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
        response = self.client.post('/admin/membership_file/member/' + str(self.member.id) + '/change/', data=self.memberData)

        # Ensure that no internal server error occurs
        self.assertNotEqual(response.status_code, 500)

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
            'email': 'newemail@email.com',
        }
        self.memberData = {**self.memberData, **updatedFields}

        # Issue a POST request.
        response = self.client.post('/admin/membership_file/member/' + str(self.member.id) + '/change/', data=self.memberData)

        # Ensure that no internal server error occurs
        self.assertNotEqual(response.status_code, 500)

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
            'email': 'newemail@email.com',
            'marked_for_deletion': 'on',
        }
        self.memberData = {**self.memberData, **updatedFields}

        # Issue a POST request.
        response = self.client.post('/admin/membership_file/member/' + str(self.member.id) + '/change/', data=self.memberData)

        # Ensure that no internal server error occurs
        self.assertNotEqual(response.status_code, 500)

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
# @param self An instance of the MemberUpdateTest-class
# @pre self != None
# @returns The Insertlog that was created
def member_got_correctly_added(self: MemberUpdateTest) -> MemberLog:
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
# @param self An instance of the MemberUpdateTest-class
# @param updatedFields The fields that were updated
# @pre self != None
# @returns The UPDATE-log that was created
def member_got_correctly_updated(self: MemberUpdateTest, updatedFields: dict) -> MemberLog:
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



#TODO: the following testcases:
# members marked for deletion:
# - cannot be deleted by the user that marked it for deletion
# - cannot have their info edited (apart from marked_for_deletion)
#