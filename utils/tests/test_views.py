
from django.contrib.auth.models import Group
from django.test import TestCase, RequestFactory
from django.views.generic import ListView, FormView
from django.forms import Form


from utils.views import SearchFormMixin, RedirectMixin

class TestForm(Form):
    pass

class TestRedirectMixin(TestCase):
    class TestView(RedirectMixin, FormView):
        success_url = "/success/"
        form_class = TestForm

    def _build_for_url(self, url, **init_kwargs):
        request = RequestFactory().get(url)

        view = self.TestView(**init_kwargs)
        view.setup(request)
        return view

    def test_succes_url_normal(self):
        # No redirect, so normal success_url needs to be used
        view = self._build_for_url('')
        url = view.get_success_url()
        self.assertEqual(url, "/success/")

    def test_succes_url_redirect(self):
        view = self._build_for_url('?redirect_to=/to_other/')
        url = view.get_success_url()
        self.assertEqual(url, "/to_other/")

    def test_redirect_url_name(self):
        url = '?on_success=/test_detour/'
        view = self._build_for_url(url, redirect_url_name='on_success' )
        url = view.get_success_url()
        self.assertEqual(url, "/test_detour/")

    def test_context_data(self):
        view = self._build_for_url('?redirect_to=/test_url/')
        context = view.get_context_data()
        self.assertIn('redirect_to_url', context.keys())
        self.assertEqual(context['redirect_to_url'], "/test_url/")


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
