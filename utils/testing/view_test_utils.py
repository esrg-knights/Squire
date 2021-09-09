
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Group, User
from django.http import Http404
from django.test import Client, RequestFactory
from django.views.generic.base import TemplateView


class ViewValidityMixin:
    """ A mixin for testing views. Takes over a bit of behind the scenes overheasd
    base_user_id: the id for the user running the sessions normally
    base_url: The basic url to navigate to
    """

    client = None
    user = None
    base_user_id = None
    base_url = None

    def setUp(self):
        self.client = Client()

        if self.base_user_id:
            self.user = User.objects.get(id=self.base_user_id)
            self.client.force_login(self.user)

    def get_base_url(self):
        return self.base_url

    def assertValidGetResponse(self, data=None, url=None):
        """
        Assert that there is a valid HTTP200 response returned
        :param data: Get data, defaults to an empty dict
        :param url: The url, defaults to self.get_base_url
        :return: Either a raised assertion error or the HttpResponse instance
        """
        url = url or self.get_base_url()
        data = data or {}
        response = self.client.get(url, data=data)
        self.assertEqual(response.status_code, 200, "Response was not a valid Http200 response")
        return response

    def assertValidPostResponse(self, data=None, url=None, redirect_url=None, fetch_redirect_response=True):
        """
        Assert that a post does not create errors
        :param data: Get data, defaults to an empty dict
        :param url: The url, defaults to self.get_base_url
        :param redirect_url: Check the url it redirects to
        :param fetch_redirect_response: Whether the page that it redirects to needs to be checked for errors. (True)
        :return: Either a raised assertion error or the HttpResponse instance
        """
        url = url or self.get_base_url()
        data = data or {}
        response = self.client.post(url, data=data)
        if redirect_url:
            self.assertRedirects(response, redirect_url, fetch_redirect_response=fetch_redirect_response)
        else:
            self.assertEqual(response.status_code, 200, "Response was not a valid Http200 response")
        return response

    @staticmethod
    def assertHasMessage(response, level=None, text=None):
        """
        Assert that the response contains a specific message
        :param response: The response object
        :param level: The level of the message (messages.SUCCESS/ EROOR or custom...)
        :param text: (part of) the message string that it should contain
        :param print_all: prints all messages encountered useful to trace errors if present
        :return: Raises AssertionError if not asserted
        """
        for message in response.context['messages']:
            # if print_all:
            #     print(message)
            if message.level == level or level is None:
                if text is None or str(text) in message.message:
                    return

        if level or text:
            msg = "There was no message for the given criteria: "
            if level:
                msg += f"level: '{level}' "
            if text:
                msg += f"text: '{text}' "
        else:
            msg = "There was no message"

        raise AssertionError(msg)


class TestMixinMixin:
    mixin_class = None
    base_user_id = None
    pre_inherit_classes = []
    view = None

    def _build_get_response(self, url=None, url_kwargs=None, save_view = True):
        url = url or self.get_base_url()
        url_kwargs = url_kwargs or self.get_base_url_kwargs()

        request = RequestFactory().get(url)
        self._imitiate_request_middleware(request)

        view = self.get_as_full_view_class()()
        view.setup(request, **url_kwargs)
        response = view.dispatch(request, **url_kwargs)

        if save_view:
            self.view = view

        return response

    def _imitiate_request_middleware(self, request):
        if self.base_user_id:
            request.user = User.objects.get(id=self.base_user_id)


    def get_base_url(self):
        return ""

    def get_base_url_kwargs(self):
        return {}

    def get_as_full_view_class(self):
        classes = self.pre_inherit_classes + [self.mixin_class]

        class MixinTestView(*classes, TemplateView):
            template_name = "utils/testing/test_mixin_template.html"

        return MixinTestView

    def assertRaises404(self, url_kwargs=None):
        try:
            self._build_get_response(url_kwargs=url_kwargs)
        except Http404:
            pass
        else:
            raise AssertionError("No '404: Page not Found' error was raised")

    def assertRaises403(self, url_kwargs=None):
        try:
            self._build_get_response(url_kwargs=url_kwargs)
        except PermissionDenied:
            pass
        else:
            raise AssertionError("No '403: Permission Denied' error was raised")
