
from django.contrib.auth.models import Group
from django.test import TestCase, RequestFactory
from django.views.generic import ListView


from utils.views import SearchFormMixin


class TestSearchFormMixin(TestCase):

    class TestView(SearchFormMixin, ListView):
        # Fictive view for testing the mixin
        model = Group
        filter_field_name = 'name'

    def setUp(self):
        Group.objects.create(name="Test group 2")
        Group.objects.create(name="A test state")
        Group.objects.create(name="Test group 1")
        Group.objects.create(name="some other group")

        self.request = RequestFactory().get('?search_field=group')

        self.view = self.TestView()
        self.view.setup(self.request)
        self.response = self.view.dispatch(self.request)

    def test_get_filter_form(self):
        form = self.view.get_filter_form()
        self.assertEqual(form.__class__.__name__, 'FilterByFieldForm')

    def test_context_data(self):
        context = self.view.get_context_data()
        self.assertIn('filter_form', context.keys())
        self.assertEqual(context['filter_form'], self.view.search_form)

    def test_get_queryset(self):
        self.assertEqual(self.view.get_queryset().count(), 3)
