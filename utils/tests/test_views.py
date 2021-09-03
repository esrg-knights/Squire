from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group
from django.contrib.messages import constants
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase, RequestFactory
from django.views.generic import ListView, FormView
from django.forms import Form, BooleanField


from utils.views import SearchFormMixin, RedirectMixin, PostOnlyFormViewMixin


class TestForm(Form):
    fail_clean = BooleanField(initial=False, required=False)
    display_success_message = BooleanField(initial=False, required=False)

    def clean(self):
        if self.cleaned_data["fail_clean"] == True:
            raise ValidationError("Test error was triggered", code='testerror')
        return self.cleaned_data

    def save(self):
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


class TestPostOnlyFormViewMixin(TestCase):

    class TestView(PostOnlyFormViewMixin, FormView):
        form_class = TestForm
        success_url = '/succes/'

        def get_success_message(self, form):
            if form.cleaned_data['display_success_message']:
                return "Success triggered"
            return None

    def _build_for_url(self, url='', http_method='post', data=None, **init_kwargs):
        request = getattr(RequestFactory(), http_method)(url, data=data)

        # Requsetfactory does not support middleware, so it should be added manually
        # adding session
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()

        # adding messages
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)

        view = self.TestView(**init_kwargs)
        view.setup(request)
        response = view.dispatch(request)
        return response, request

    def test_get(self):
        """ Tests that a get defaults back to the normal page and displays an access error"""
        response, request = self._build_for_url(http_method='get')

        self.assertEqual(response.status_code, 302)  # Test Redirect code
        self.assertEqual(response.url, self.TestView.success_url)

        self.assertEqual(self.get_first_message(request).level, constants.WARNING)

    def test_post_invalid(self):
        response, request = self._build_for_url(data={'fail_clean': True})

        self.assertEqual(response.status_code, 302)  # Test Redirect code
        self.assertEqual(response.url, self.TestView.success_url)

        message_obj = self.get_first_message(request)
        self.assertEqual(message_obj.level, constants.WARNING)
        self.assertEqual(message_obj.message, "Action could not be performed; "+"Test error was triggered")



    def test_post_valid_messageless(self):
        response, request = self._build_for_url(data={'fail_clean': False})

        self.assertEqual(response.status_code, 302)  # Test Redirect code
        self.assertEqual(response.url, self.TestView.success_url)

        self.assertEqual(len(request._messages), 0)

    def test_post_valid_message(self):
        response, request = self._build_for_url(data={'display_success_message': True})

        message_obj = self.get_first_message(request)
        self.assertEqual(message_obj.level, constants.SUCCESS)
        self.assertEqual(message_obj.message, "Success triggered")

    def get_first_message(self, request):
        """ Returns the first message in the messages framework"""
        for message in request._messages:
            # This is weird, but searching with [0] provides an error. So I do this instead
            return message







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
