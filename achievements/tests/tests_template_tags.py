from django.test import TestCase
from django.template import Context, Template

# Tests usage of custom template tags and filters
class TemplateTagsTest(TestCase):
    # Tests the negate template tag
    def test_negate(self):
        out = Template(
            "{% load negate %}"
            "{{ number_positive|negate }}<br>"
            "{{ number_negative|negate }}<br>"
            "{{ number_zero|negate }}"
        ).render(Context({
            'number_positive': 8,
            'number_negative': -34,
            'number_zero':  0,
        }))
        self.assertEqual(out, "-8<br>34<br>0")

    # Tests the format string template tag
    def test_format_string(self):
        out = Template(
            "{% load format_string %}"
            "{% format_string '{1}, {0} {1}' 'James' 'Bond' %}<br>"
            "{% format_string 'My name is {0}' 'Oscar' %}<br>"
            "{% format_string 'This does not take any parameters!' %}"
        ).render(Context())
        self.assertEqual(out, "Bond, James Bond<br>My name is Oscar<br>This does not take any parameters!")

    # Tests the subtract template tag
    def test_subtract(self):
        out = Template(
            "{% load subtract %}"
            "{{ 2|subtract:1 }}<br>"
            "{{ 2|subtract:5 }}"
        ).render(Context())
        self.assertEqual(out, "1<br>-3")

    # Tests the filter_first template tag
    def test_filter_first(self):
        out = Template(
            "{% load filter_first %}"
            "{% for item in lst|filter_first:0 %}"
                "{{item}}<br>"
            "{% endfor %}"
            "<br><br>"
            "{% for item in lst|filter_first:2 %}"
                "{{item}}<br>"
            "{% endfor %}"
        ).render(Context({
            'lst': [1, 'blah', -5],
        }))
        self.assertEqual(out, "<br><br>1<br>blah<br>")
