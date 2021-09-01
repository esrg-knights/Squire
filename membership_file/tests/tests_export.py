import csv
from io import StringIO

from django.test import TestCase

from membership_file.models import Room

from membership_file.export import MemberResource


class MembershipFileExportTest(TestCase):
    """ Tests the structure of the exported membership file """
    fixtures = ['test_export_members.json']

    def setUp(self):
        csv_export = MemberResource().export().csv
        f = StringIO(csv_export)
        self.reader = csv.DictReader(f, delimiter=',')

    def test_email_split(self):
        """ Tests if the email addresses for registered and deregistered members are in different columns """
        for row in self.reader:
            if row['is_deregistered']:
                self.assertEqual(row['email'], "")
            else:
                self.assertEqual(row['email_deregistered_member'], "")

    def test_accessible_rooms(self):
        """ Tests if accessible rooms are added correctly """
        for row in self.reader:
            if row['id'] == 1:
                self.assertIn(str(Room.objects.get(id=1)), row["accessible_rooms"])
                self.assertIn(str(Room.objects.get(id=2)), row["accessible_rooms"])
                break
