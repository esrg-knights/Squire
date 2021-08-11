from django import forms
from django.core.paginator import Paginator
from django.template.context import Context
from django.test import TestCase
from django.test.client import RequestFactory
from django.template import Context, Template


from utils.templatetags import paginator as paginator_tags


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


class PaginatorTemplateTagTest(TestCase):

    def setUp(self):
        self.paginator_obj = Paginator(list(range(0,59)), 5)
        self.request_factory = RequestFactory()

    def test_get_url_for_page(self):
        url="/test/?data=14&page=3&oneattribute=trial&mix=42"
        request = RequestFactory().get(url)
        context = {'request': request}
        new_url = paginator_tags.get_url_for_page(context, 5)
        self.assertEqual(new_url, "?data=14&page=5&oneattribute=trial&mix=42")

    def test_paginator_standard_values(self):
        context = Context({
            'request': self.request_factory.get("/?page=2"),
            'page_obj': self.paginator_obj.get_page(2),
        })

        render_values = paginator_tags.render_paginator(context)
        self.assertIn('request', render_values)
        self.assertIn('show_range', render_values)

        self.assertEqual(render_values['current_page'], 2)
        self.assertEqual(render_values['total_pages'], 12)

    def test_patinator_values_first_page_on_render_edge(self):
        """ Tests a situation where the first page is just at the edge of the scope where it does not normally
        get displayed, but whwere page 2 is rendered"""
        context = Context({
            'request': self.request_factory.get("/?page=4"),
            'page_obj': self.paginator_obj.get_page(4),
        })
        render_values = paginator_tags.render_paginator(context)

        self.assertEqual(list(render_values['low_pages']), [2,3,])
        self.assertEqual(list(render_values['high_pages']), [5,6,])

        self.assertEqual(render_values['display_first'], True)
        self.assertEqual(render_values['display_first_with_gap'], False)
        self.assertEqual(render_values['display_last'], True)
        self.assertEqual(render_values['display_last_with_gap'], True)

    def test_paginator_max_value(self):
        """ Tests a situation where the last page is visited """
        context = Context({
            'request': self.request_factory.get("/?page=11"),
            'page_obj': self.paginator_obj.get_page(11),
        })
        render_values = paginator_tags.render_paginator(context)

        self.assertEqual(list(render_values['low_pages']), [8,9,10,])
        self.assertEqual(list(render_values['high_pages']), [12])

        self.assertEqual(render_values['display_first'], True)
        self.assertEqual(render_values['display_first_with_gap'], True)
        self.assertEqual(render_values['display_last'], False)
        self.assertEqual(render_values['display_last_with_gap'], False)
