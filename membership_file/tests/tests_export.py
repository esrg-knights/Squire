import csv
from io import StringIO

from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from import_export.formats.base_formats import YAML

from membership_file.admin import MemberWithLog, TSVUnicodeBOM
from membership_file.export import MemberResource, MembersFinancialResource
from membership_file.models import Member, Room


class MembershipFileExportTest(TestCase):
    """Tests the structure of the exported membership file"""

    fixtures = ["test_export_members.json"]

    def setUp(self):
        csv_export = MemberResource().export().csv
        f = StringIO(csv_export)
        self.reader = csv.DictReader(f, delimiter=",")

    def test_email_split(self):
        """Tests if the email addresses for registered and deregistered members are in different columns"""
        for row in self.reader:
            if row["is_deregistered"]:
                self.assertEqual(row["email"], "")
            else:
                self.assertEqual(row["email_deregistered_member"], "")

    def test_accessible_rooms(self):
        """Tests if accessible rooms are added correctly"""
        for row in self.reader:
            if row["id"] == 1:
                self.assertIn(str(Room.objects.get(id=1)), row["accessible_rooms"])
                self.assertIn(str(Room.objects.get(id=2)), row["accessible_rooms"])
                break


class MembershipFinanceFileExportTest(TestCase):
    """Tests the structure of the exported membership file"""

    fixtures = [
        "test_users",
        "test_members",
    ]

    def setUp(self):
        csv_export = MembersFinancialResource().export().csv
        f = StringIO(csv_export)
        self.reader = csv.DictReader(f, delimiter=",")

    def test_member_name(self):
        """Tests if the email addresses for registered and deregistered members are in different columns"""
        for row in self.reader:
            if self.reader.line_num == 2:
                self.assertEqual(row.get("member"), "Charlie van der Dommel")

    def test_fields(self):
        self.assertIn("member", self.reader.fieldnames)
        self.assertIn("email", self.reader.fieldnames)
        self.assertIn("year__name", self.reader.fieldnames)
        self.assertIn("has_paid", self.reader.fieldnames)

    def test_email(self):
        """Tests if the email addresses for registered and deregistered members are in different columns"""
        for row in self.reader:
            if self.reader.line_num == 2:
                self.assertEqual(row.get("email"), "linked_member@example.com")


class ModelAdminExportTest(TestCase):
    """
    Tests for the model admin's export functionality
    """

    fixtures = ["test_export_members.json"]

    def setUp(self):
        self.model_admin = MemberWithLog(model=Member, admin_site=AdminSite())

    def test_export_filename(self):
        """Tests the exported filename"""
        # Everyone (includes both)
        filename = self.model_admin.get_export_filename(None, Member.objects.all(), YAML())
        self.assertIn("HAS_DEREGISTERED_MEMBERS", filename)

        # Deregistered members only
        filename = self.model_admin.get_export_filename(None, Member.objects.filter(is_deregistered=True), YAML())
        self.assertIn("HAS_DEREGISTERED_MEMBERS", filename)

        # Registered members only
        filename = self.model_admin.get_export_filename(None, Member.objects.filter(is_deregistered=False), YAML())
        self.assertNotIn("HAS_DEREGISTERED_MEMBERS", filename)


class MembershipFileExportAsTSVTest(TestCase):
    """Tests if the BOM gets prepended"""

    fixtures = ["test_export_members.json"]

    def setUp(self):
        self.export = MemberResource().export()
        self.tsvClass = TSVUnicodeBOM()

    def test_BOM(self):
        exported_str = self.tsvClass.export_data(self.export)
        exported_str.startswith("\uFEFF")
