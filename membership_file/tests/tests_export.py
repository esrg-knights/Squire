import os

from django.conf import settings
from django.test import TestCase, override_settings

from core.tests.util import suppress_warnings
from membership_file.models import Member

output_path = os.path.join(settings.BASE_DIR, 'test', 'output')
output_file = os.path.join(output_path, 'squire_membership_file.csv')

@override_settings(MEMBERSHIP_FILE_EXPORT_PATH=output_path)
class MembershipFileExportTest(TestCase):
    fixtures = ['test_users.json', 'test_members.json']

    def remove_previous_file(self):
        if os.path.isfile(output_file):
            try: # If it does, try deleting it
                os.remove(output_file)
            except OSError as e: # If auto-deletion fails, notify the user and fail the test
                self.fail(f"Could not delete file <{output_file}> so the test could not be started. Please delete it manually.")

    # Tests if a new file is created when it does not exist
    @suppress_warnings(logger_name='membership_file')
    def test_new_member(self):
        self.remove_previous_file()

        # Create a Member
        Member.objects.create(**{
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1970-01-01",
            "email": "johndoe@example.com",
            "street": "Main Street",
            "house_number": "23",
            "city": "Los Angeles",
            "country": "USA",
            "member_since": "2000-01-01",
            "educational_institution": "LA Police Academy",
        })

        with open(output_file) as f:
            count = sum(1 for _ in f)

        # Should contain the header, old members, and the newly added member
        self.assertEqual(count, 4)

        self.remove_previous_file()

    @suppress_warnings(logger_name='membership_file')
    def test_update_member(self):
        self.remove_previous_file()

        # Update a Member
        member = Member.objects.filter(first_name='Charlie').first()
        member.first_name = "Charles"
        member.save()

        with open(output_file) as f:
            count = sum(1 for _ in f)

        # Should contain the header, old members, and updated member
        self.assertEqual(count, 3)

        self.remove_previous_file()

    @suppress_warnings(logger_name='membership_file')
    def test_remove_member(self):
        self.remove_previous_file()

        # Delete a Member
        Member.objects.filter(first_name='Charlie').delete()

        with open(output_file) as f:
            count = sum(1 for _ in f)

        # Should contain the header, old members, not the deleted member
        self.assertEqual(count, 2)

        self.remove_previous_file()
