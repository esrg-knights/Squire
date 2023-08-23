from django.test import TestCase

from committees.url_converters import AssociationgroupConverter
from committees.models import *


class TestAssociationgroupConverter(TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "committees/associationgroups"]

    def setUp(self):
        self.converter = AssociationgroupConverter()

    def test_to_python(self):
        self.assertEqual(self.converter.to_python("3"), AssociationGroup.objects.get(id=3))

    def test_to_python_fails(self):
        # Assure it fails on non-existent associationgroups
        self.assertRaises(ValueError, self.converter.to_python, 99)

    def test_to_url(self):
        # Test on the contenttype instance
        self.assertEqual(self.converter.to_url(AssociationGroup.objects.get(id=1)), 1)
        self.assertEqual(self.converter.to_url(AssociationGroup.objects.get(id=3)), 3)

    def test_to_url_fails(self):
        with self.assertRaises(AssertionError):
            self.converter.to_url("not_a_string")
        with self.assertRaises(AssertionError):
            self.converter.to_url(AssociationGroupMembership.objects.first())
