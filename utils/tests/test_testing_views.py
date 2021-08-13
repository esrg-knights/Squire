
from django.contrib.auth import get_user, PermissionDenied
from django.contrib.auth.models import User
from django.contrib.messages import add_message, DEBUG, ERROR, SUCCESS
from django.contrib.messages.storage.base import Message
from django.http import HttpResponse, Http404, HttpResponseForbidden, HttpResponseRedirect
from django.test import TestCase
from django.views.generic import View

from utils.tests import raisesAssertionError
from utils.testing.view_test_utils import ViewValidityMixin, TestMixinMixin


class TestMessageView(View):

    def dispatch(self, request, *args, level=None, msg=None, **kwargs):
        add_message(request, level, message=msg)
        return HttpResponse()


class FakeClient:
    """ A fake client to test get and post assert methods with """
    def __init__(self, http_class, **kwargs):
        self.http_class = http_class
        self.http_init_kwargs = kwargs

    def get(self, *args, **kwargs):
        return self.http_class(**self.http_init_kwargs)

    def post(self, *args, **kwargs):
        return self.get(*args, **kwargs)


class TestViewValidityMixin(ViewValidityMixin, TestCase):
    base_url = "test/something-else/"

    def setUp(self):
        user = User.objects.create()
        self.base_user_id = user.id
        super(TestViewValidityMixin, self).setUp()

    def test_setup(self):
        user = User.objects.last()
        self.assertEqual(self.user, user)
        self.assertIsNotNone(self.client)
        # Check that the user is authenticated
        self.assertTrue(get_user(self.client).is_authenticated)

    def test_get_base_url(self):
        self.assertEqual(self.get_base_url(), self.base_url)

    def get_fake_client_instance(self, http_response_class, **http_init_kwargs):
        return FakeClient(http_response_class, **http_init_kwargs)

    def test_valid_get_response(self):
        self.client = FakeClient(HttpResponse)
        self.assertValidGetResponse()

        # Assert that it fails when presented a forbidden page
        self.client = FakeClient(HttpResponseForbidden)
        error = raisesAssertionError(
            self.assertValidGetResponse
        )
        self.assertEqual(error.__str__(), "403 != 200 : Response was not a valid Http200 response")

    def assertRedirects(self, response, *args, **kwargs):
        # Overwrite to serve as checkpoint
        if not isinstance(response, HttpResponseRedirect):
            raise AssertionError("RedirectCheck")

    def test_valid_post_response(self):
        self.client = FakeClient(HttpResponse)
        self.assertValidPostResponse()

        # Assert that redirection is checked through self.assertsRedirect as that is validated as working
        error = raisesAssertionError(self.assertValidPostResponse, redirect_url="/wrong-link/")
        self.assertEqual(error.__str__(), "RedirectCheck")
        # Set httpresponse class to redirect
        self.client = FakeClient(HttpResponseRedirect, redirect_to="/correct-link/")
        self.assertValidPostResponse(redirect_url="/correct-link/")

        # Assert that it fails when presented a forbidden page
        self.client = FakeClient(HttpResponseForbidden)
        error = raisesAssertionError(self.assertValidPostResponse)
        self.assertEqual(error.__str__(), "403 != 200 : Response was not a valid Http200 response")


    def test_has_message(self):
        # Messages are read through the response.context property.
        # We can imitate that as long as the messages are actual messages.
        class FakeResponse:
            context = {
            'messages':[
                Message(DEBUG, 'test_debug_message'),
                Message(ERROR, 'test_error_message'),
            ]}
        response = FakeResponse()

        self.assertHasMessage(response, DEBUG, "test_debug_message")
        self.assertHasMessage(response, ERROR, "test_error_message")

        # Incorrect text
        error = raisesAssertionError(self.assertHasMessage, response, ERROR, "test_message")
        self.assertEqual(error.__str__(),
            "There was no message for the given criteria: level: '{level}' text: '{text}' ".format(
                level=ERROR,
                text="test_message"
        ))

        error = raisesAssertionError(self.assertHasMessage, response, SUCCESS)
        self.assertEqual(error.__str__(), "There was no message for the given criteria: level: '{level}' ".
                         format(level=SUCCESS))


class TestableMixin:

    def get(self, request, *args, **kwargs):
        if 'deny' in kwargs.keys():
            raise PermissionDenied()
        if 'lost' in kwargs.keys():
            raise Http404()
        else:
            return super(TestableMixin, self).get(request, *args, **kwargs)


class TestTestMixinMin(TestMixinMixin, TestCase):
    mixin_class = TestableMixin

    def setUp(self):
        self.base_user_id = User.objects.create().id

    def test_build_get_response(self):
        self._build_get_response(save_view=True)

        # Test that it logged in the set user
        self.assertEqual(self.view.request.user.id, self.base_user_id)
        self.assertTrue(self.view.request.user.is_authenticated)

    def test_assertRaises404(self):
        self.assertRaises404(url_kwargs={'lost': True})

        error = raisesAssertionError(self.assertRaises404)
        self.assertEqual(error.__str__(), "No '404: Page not Found' error was raised")

    def test_assertRaises403(self):
        self.assertRaises403(url_kwargs={'deny': True})

        error = raisesAssertionError(self.assertRaises403)
        self.assertEqual(error.__str__(), "No '403: Permission Denied' error was raised")
