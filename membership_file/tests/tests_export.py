import csv
from io import StringIO

from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from import_export.formats.base_formats import YAML

from membership_file.admin import MemberWithLog
from membership_file.export import MemberResource
from membership_file.models import Member, Room


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

class ModelAdminExportTest(TestCase):
    """
        Tests for the model admin's export functionality
    """
    fixtures = ['test_export_members.json']

    def setUp(self):
        self.model_admin = MemberWithLog(model=Member, admin_site=AdminSite())

    def test_export_filename(self):
        """ Tests the exported filename """
        # Everyone (includes both)
        filename = self.model_admin.get_export_filename(None, Member.objects.all(), YAML())
        self.assertIn("HAS_DEREGISTERED_MEMBERS", filename)

        # Deregistered members only
        filename = self.model_admin.get_export_filename(None, Member.objects.filter(is_deregistered=True), YAML())
        self.assertIn("HAS_DEREGISTERED_MEMBERS", filename)

        # Registered members only
        filename = self.model_admin.get_export_filename(None, Member.objects.filter(is_deregistered=False), YAML())
        self.assertNotIn("HAS_DEREGISTERED_MEMBERS", filename)
