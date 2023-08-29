from django.test import TestCase

from committees.models import AssociationGroup
from committees.url_converters import AssociationgroupConverter


class AssociationGroupConverterTestCase(TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "committees/associationgroups"]

    def setUp(self):
        self.converter = AssociationgroupConverter()

    def test_to_python_nonexistent(self):
        with self.assertRaises(ValueError):
            self.converter.to_python(999)

    def test_to_python(self):
        self.assertEqual(self.converter.to_python(3).id, 3)

    def test_to_url_from_int(self):
        self.assertEqual(self.converter.to_url(2), 2)

    def test_to_url_from_group(self):
        self.assertEqual(self.converter.to_url(AssociationGroup.objects.get(id=1)), 1)
