from django.test import TestCase
from django.contrib.contenttypes.models import ContentType

from inventory.urls import CatalogueConverter
from inventory.models import *


class TestCatalogueConverter(TestCase):

    def setUp(self):
        self.converter = CatalogueConverter()

    def test_to_python(self):
        # self.assertEqual(self.converter.to_python('boardgame'),
        #                  ContentType.objects.get_for_model(BoardGame))
        self.assertEqual(self.converter.to_python('miscellaneousitem'),
                         ContentType.objects.get_for_model(MiscellaneousItem))

    def test_to_python_fails(self):
        # Assure it fails on non-existent models
        self.assertRaises(ValueError, self.converter.to_python, 'nonexistentmodel')
        # Assure it fails on instances that are not an item
        self.assertRaises(ValueError, self.converter.to_python, 'ownership')

    def test_to_url(self):
        # Test on the contenttype instance
        self.assertEqual(self.converter.to_url(ContentType.objects.get_for_model(MiscellaneousItem)), 'miscellaneousitem')

