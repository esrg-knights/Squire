from django.core.exceptions import ValidationError
from django.forms import CharField
from django.test.testcases import TestCase
from django.utils.safestring import SafeText
from martor.fields import MartorFormField

from core.fields import MarkdownObject, MarkdownCharField


class MarkdownObjectTest(TestCase):
    """ Tests for MarkdownObject """
    def setUp(self):
        self.raw = "Look at **this**. Isnt it [nice](https://kotkt.nl)?"
        self.plaintext = "Look at this. Isnt it nice?"
        self.rendered = "<p>Look at <strong>this</strong>. Isnt it <a href=\"https://kotkt.nl\">nice</a>?</p>"

        self.md_object = MarkdownObject(self.raw)

    def test_raw(self):
        """ Tests if raw MD is returned """
        output = self.md_object.as_raw()
        self.assertEqual(output, self.raw)
        self.assertNotIsInstance(output, SafeText)

    def test_plaintext(self):
        """ Tests if stripped MD is returned """
        output = self.md_object.as_plaintext()
        self.assertEqual(output, self.plaintext)
        self.assertIsInstance(output, SafeText)

    def test_rendered(self):
        """ Tests if rendered MD is returned """
        output = self.md_object.as_rendered()
        self.assertEqual(output, self.rendered)
        self.assertIsInstance(output, SafeText)

    def test_html_escaped(self):
        """ Tests if HTML that is not created by markdown is escaped """
        unsafe_text = "<script>alert('hello!')</script>"
        escaped_text = "&lt;script&gt;alert(&lsquo;hello!&rsquo;)&lt;/script&gt;"

        md_object = MarkdownObject(unsafe_text)
        self.assertEqual(md_object.as_raw(), unsafe_text)
        self.assertEqual(md_object.as_plaintext(), escaped_text)
        self.assertEqual(md_object.as_rendered(), f"<p>{escaped_text}</p>")


class MarkdownFieldMixinTest(TestCase):
    """
        Tests for MarkdownFieldMixin
    """
    def setUp(self):
        self.charfield = MarkdownCharField(max_length=12)

    def test_max_length(self):
        """ Tests if the max_length property is still enforced"""
        with self.assertRaisesMessage(ValidationError, "Ensure this value has at most 12 characters (it has 13)"):
            self.charfield.run_validators(MarkdownObject("1234567890abc"))

    def test_to_python(self):
        """ Tests for to_python(val) -> Convert from any value to a MarkdownObject """
        # Bogus data
        output = self.charfield.to_python(4)
        self.assertEqual(output, MarkdownObject("4"))

        # None
        output = self.charfield.to_python(None)
        self.assertIsNone(output)

        # Another MarkdownObject
        output = self.charfield.to_python("cool *markdown*")
        self.assertEqual(output, MarkdownObject("cool *markdown*"))

    def test_from_db_value(self):
        """ Tests for from_db_value(val) -> Convert from database to a MarkdownObject """
        # None
        output = self.charfield.from_db_value(None, None, None)
        self.assertIsNone(output)

        # str
        output = self.charfield.from_db_value("cool *markdown*", None, None)
        self.assertEqual(output, MarkdownObject("cool *markdown*"))

    def test_get_prep_value(self):
        """ Tests for get_prep_value(val) -> Convert from MDObject to Database-ready input """
        # None
        output = self.charfield.get_prep_value(None)
        self.assertIsNone(output)

        # str
        output = self.charfield.get_prep_value("cool *markdown*")
        self.assertEqual(output, "cool *markdown*")

        # MDObject
        output = self.charfield.get_prep_value(MarkdownObject("cool *markdown*"))
        self.assertEqual(output, "cool *markdown*")


    def test_value_to_string(self):
        """
            Tests for value_to_string(obj) -> Convert an obj instance field to
            a string (for serialization)
        """
        # Cheat a little; we're not using a Model
        class FakeModel:
            my_field = None
        self.charfield.attname = "my_field"
        fake_model_obj = FakeModel()

        # None
        output = self.charfield.value_to_string(fake_model_obj)
        self.assertIsNone(output)

        # str
        fake_model_obj.my_field = "cool *markdown*"
        output = self.charfield.value_to_string(fake_model_obj)
        self.assertEqual(output, "cool *markdown*")

        # MDObject
        fake_model_obj.my_field = MarkdownObject("cool *markdown*")
        output = self.charfield.value_to_string(fake_model_obj)
        self.assertEqual(output, "cool *markdown*")

    def test_formfield(self):
        """ Tests if formfield attributes are not overridden if not needed """
        # Default
        result = self.charfield.formfield()
        self.assertIsNotNone(result)
        self.assertIsInstance(result, MartorFormField)

        # Overridden kwargs
        result = self.charfield.formfield(form_class=CharField, max_length=3)
        self.assertIsNotNone(result)
        self.assertEqual(result.max_length, 3)
        self.assertIsInstance(result, CharField)
