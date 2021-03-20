from django.test import TestCase
from django.test.client import RequestFactory
from django.template import Context, Template

# Tests usage of custom template tags and filters
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
