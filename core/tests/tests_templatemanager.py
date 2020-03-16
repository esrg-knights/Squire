from django.test import TestCase

from core.views import TemplateManager

##################################################################################
# Test the TemplateManager
# @since 16 MAR 2020
##################################################################################

# Tests the TemplateManager's get and set methods
class TemplateManagerTest(TestCase):

    # Tests get method
    def test_get_none(self):
        self.assertIsNone(TemplateManager.get_template("test"))

    # Tests set method
    def test_get_not_none(self):
        TemplateManager.set_template("woof", "dog")
        TemplateManager.set_template("meow", "cat")
        TemplateManager.set_template("blub", "fish")

        self.assertEqual("dog", TemplateManager.get_template("woof"))
        self.assertEqual("cat", TemplateManager.get_template("meow"))
        self.assertEqual("fish", TemplateManager.get_template("blub"))


