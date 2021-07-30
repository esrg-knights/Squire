
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth.models import Group, User
from django.http import HttpResponse, Http404
from django.test import TestCase, Client, RequestFactory
from django.utils import timezone
from django.urls import reverse
from django.views.generic.base import TemplateView


class ViewValidityMixin:
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

    @staticmethod
    def assertHasMessage(response, level=None, text=None, print_all=False):
        """
        Assert that the response contains a specific message
        :param response: The response object
        :param level: The level of the message (messages.SUCCESS/ EROOR or custom...)
        :param text: (part of) the message string that it should contain
        :param print_all: prints all messages encountered useful to trace errors if present
        :return: Raises AssertionError if not asserted
        """
        for message in response.context['messages']:
            if print_all:
                print(message)
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
        if self.base_user_id:
            request.user = User.objects.get(id=self.base_user_id)

        view = self.get_as_full_class()()
        view.setup(request, **url_kwargs)
        response = view.dispatch(request)

        if save_view:
            self.view = view

        return response


    def get_base_url(self):
        return ""

    def get_base_url_kwargs(self):
        return {}

    def get_as_full_class(self):
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
            raise AssertionError("No '404: Page not Found' error was raised")
