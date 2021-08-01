
from django.contrib.auth.models import Group
from django.test import TestCase

from utils.forms import get_basic_filter_by_field_form
from utils.testing import FormValidityMixin


class TestBasicFilterForm(FormValidityMixin, TestCase):

    def setUp(self):
        Group.objects.create(name="Test group 2")
        Group.objects.create(name="A test state")
        Group.objects.create(name="Test group 1")
        Group.objects.create(name="some other group")

        self.form_class = get_basic_filter_by_field_form('name')

    def test_filtering(self):
        self.assertEqual(self.filter_for('group').count(), 3)
        self.assertEqual(self.filter_for('up 1').count(), 1)

    def test_case_insensitive(self):
        self.assertEqual(self.filter_for('test').count(), 3)

    def test_ordering(self):
        self.assertEqual(self.filter_for('test').first().name, "A test state")

    def filter_for(self, search_string):
        """ Returns a form-filtered queryset of the Groups for given search_string """
        form = self.form_class({'search_field': search_string})
        if form.is_valid():
            return form.get_filtered_items(Group.objects.all())
        raise AssertionError("Somehow form was not deemed valid?")







