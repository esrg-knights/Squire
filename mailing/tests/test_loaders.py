from django.test import TestCase
from django.template import Engine

from mailing.loaders import CustomAppDirectoryLoader




class CustomAppDirectoryLoaderTestCase(TestCase):

    def setUp(self):
        self.engine = Engine()

    def test_loader(self):
        loader = CustomAppDirectoryLoader(
            self.engine,
            "tests/test_templates"
        )
        self.assertIsNotNone(loader.get_template("test_loader_template.html"))
