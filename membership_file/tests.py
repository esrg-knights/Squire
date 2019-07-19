from django.test import TestCase
from django.test import Client
from .models import Member, MemberLog, MemberLogField
from django.contrib.auth.models import User

##################################################################################
# Test cases for MemberLog-logic and Member deletion logic
# @author E.M.A. Arts
# @since 19 JUL 2019
##################################################################################


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
        pass

    def setUp(self):
        # Called each time before a testcase runs
        # Set up data for each test.
        # Objects are refreshed here and a client (to make HTTP-requests) is created here
        self.client = Client()
        
        # Create normal user and admin here
        self.user = User.objects.create(username="username", password="password")
        self.user2 = User.objects.create(username="username2", password="password")
        self.admin = User.objects.create_superuser(username="admin", password="admin", email="")
        User.save(self.user)
        User.save(self.user2)
        User.save(self.admin)

        # Define test data
        self.email = "info@kotkt.nl"
        self.data = {
            "user": "",
            "first_name": "Knights",
            "tussenvoegsel": "of the",
            "last_name": "Kitchen Table",
            "tue_card_number": "",
            "external_card_number": "",
            "external_card_cluster": "",
            "date_of_birth": "01/01/1970",
            "email": self.email,
            "phone_number": "",
            "street": "De Lampendriessen",
            "house_number": "31",
            "house_number_addition": "11",
            "city": "Eindhoven",
            "state": "Noord-Brabant",
            "country": "The Netherlands",
            "postal_code": "5612 AH",
            "member_since": "01/01/1970",
        }
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
        deleteLogs = MemberLog.objects.filter(
            user__id = self.admin.id,
            member__id = member.id,
            log_type = "DELETE",
        )

        # Only 1 DELETE-log should exist
        self.assertEqual(1, deleteLogs.count())
        deleteLog = deleteLogs.first()

        # A DELETE-log does not have fields
        self.assertIsNone(MemberLogField.objects.filter(member_log__id = deleteLog.id).first())

        # The DELETE-log should be created later than the INSERT-log
        self.assertGreater(deleteLog.id, insertLog.id)
        


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
    self.assertEqual(self.numNonEmptyFields + 1, MemberLogField.objects.filter(member_log__id = memberLog.id).count())

    return memberLog


#TODO: the following testcases:
# members marked for deletion:
# - cannot be deleted by the user that marked it for deletion
# - cannot have their info edited (apart from marked_for_deletion)
#
# creating a member:
# - creates an INSERT logentry
#
# updating member info (without marked_for_deletion=True)
# - creates an UPDATE logentry
#
# setting marked_for_deletion = True
# - creates a DELETE entry (and no associated fields)
#