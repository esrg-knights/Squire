from django import forms
from django.test import TestCase
from django.test.client import RequestFactory
from django.template import Context, Template

###########################################################
# Tests usage of custom template tags and filters
###########################################################

# A form containing three common input options (text, select, checkbox)
class DummyForm(forms.Form):
    test_charfield = forms.CharField()
    test_select = forms.ChoiceField(choices=[
        ('A', 'Alpha'),
        ('B', 'Bravo'),
        ('C', 'Charlie'),
    ])
    test_booleanfield = forms.BooleanField()

# Tests generic_field. Used by most forms
class GenericFieldTemplateTagTest(TestCase):
    def setUp(self):
        form_data = {
            'test_charfield': 'text',
            'test_select': 'A',
            'test_booleanfield': True
        }
        self.form = DummyForm(data=form_data)

    # Tests a form with a single charfield
    def test_generic_field_single_charfield(self):
        out = Template("{% load generic_field %}{% generic_field form.test_charfield -1 %}"
            ).render(Context({ 'form': self.form }))

        # Test key parts of output (single input, no labels)
        self.assertEqual(out.count('<input type="text" name="test_charfield"'), 1)
        self.assertEqual(out.count('<div class="input-group">'), 1)
        self.assertEqual(out.count('<span class="input-group-text'), 1)
        self.assertNotIn('<label class="form-check-label"', out)

    # Tests a form with a single select
    def test_generic_field_single_select(self):
        out = Template("{% load generic_field %}{% generic_field form.test_select -1 %}"
            ).render(Context({ 'form': self.form }))

        # Test key parts of output (select, option, single input group, no label)
        self.assertEqual(out.count('<select name="test_select"'), 1)
        self.assertEqual(out.count('<option value='), 3)
        self.assertEqual(out.count('<div class="input-group">'), 1)
        self.assertEqual(out.count('<span class="input-group-text'), 1)
        self.assertNotIn('<label class="form-check-label"', out)

    # Tests a formgroup with only checkboxes (renders with a label instead of prepends)
    def test_generic_field_checkboxes(self):
        # Single checkbox
        out = Template("{% load generic_field %}{% generic_field form.test_booleanfield -1 %}"
            ).render(Context({ 'form': self.form }))

        # Test key parts of output (single label, no non-checkbox inputs)
        self.assertNotIn('<input type="text"', out)
        self.assertNotIn('<option', out)
        self.assertEqual(out.count('<div class="input-group">'), 1)
        self.assertEqual(out.count('<input type="checkbox"'), 1)
        self.assertEqual(out.count('<div class="form-check form-check-inline'), 1)
        self.assertEqual(out.count('<label class="form-check-label"'), 1)

        # Multiple Checkboxes
        out = Template("{% load generic_field %}{% generic_field form.test_booleanfield form.test_booleanfield -1 -1 %}"
            ).render(Context({ 'form': self.form }))

        # Test key parts of output (single label, no non-checkbox inputs)
        self.assertNotIn('<input type="text"', out)
        self.assertNotIn('<option', out)
        self.assertEqual(out.count('<div class="input-group">'), 1)
        self.assertEqual(out.count('<input type="checkbox"'), 2)
        self.assertEqual(out.count('<div class="form-check form-check-inline'), 2)
        self.assertEqual(out.count('<label class="form-check-label"'), 2)

    # Tests a form for a combination of text inputs and checkboxes
    #   (renders with prepends and without labels, due to the lack of better options)
    def test_generic_field_checkbox_and_other(self):
        # Single checkbox
        out = Template("{% load generic_field %}{% generic_field form.test_booleanfield form.test_charfield -1 -1 %}"
            ).render(Context({ 'form': self.form }))

        # Test key parts of output (single label, no non-checkbox inputs)
        self.assertEqual(out.count('<div class="input-group">'), 1)
        self.assertEqual(out.count('<span class="input-group-text'), 2)
        self.assertEqual(out.count('<input type="text"'), 1)
        self.assertEqual(out.count('<input type="checkbox"'), 1)
        self.assertNotIn('<div class="form-check form-check-inline', out)
        self.assertNotIn('<label class="form-check-label"', out)

# Build absolute uri's (used for OpenGraph Link Previews)
class BuildAbsoluteURITemplateTagTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    # Match behaviour if left empty
    def test_build_absolute_uri_empty(self):
        request = self.factory.get('/some_location')
        out = Template(
            "{% load build_absolute_uri %}"
            "{% build_absolute_uri request %}"
        ).render(Context({
            'request': request
        }))
        self.assertEqual(out, request.build_absolute_uri())

    # Match behaviour if filled
    def test_build_absolute_uri_not_empty(self):
        request = self.factory.get('/some_location')
        out = Template(
            "{% load build_absolute_uri %}"
            "{% build_absolute_uri request 'some_cool_url' %}"
        ).render(Context({
            'request': request
        }))
        self.assertEqual(out, request.build_absolute_uri('/some_cool_url'))

    # Prepend /static directory for images
    def test_build_absolute_image_uri(self):
        request = self.factory.get('/some_location')
        out = Template(
            "{% load build_absolute_uri %}"
            "{% build_absolute_image_uri request 'image_located_in_static' %}"
        ).render(Context({
            'request': request
        }))
        self.assertEqual(out, request.build_absolute_uri('static/image_located_in_static'))
