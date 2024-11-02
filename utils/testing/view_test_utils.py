from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Group, User, Permission
from django.contrib.messages import constants as msg_constants
from django.http import Http404, HttpResponse
from django.template.response import TemplateResponse
from django.test import Client, RequestFactory
from django.views.generic.base import TemplateView

from core.tests.util import suppress_warnings


class ViewValidityMixin:
    """A mixin for testing views. Takes over a bit of behind the scenes overhead
    base_user_id: the id for the user running the sessions normally
    base_url: The basic url to navigate to
    permission_required: The name (or list of names) of the permission(s) that is required to view the tested page
    """

    client = None
    user = None
    base_user_id = None
    base_url = None
    permission_required = None
    form_context_name = "form"

    def setUp(self):
        self.client = Client()

        if self.base_user_id:
            self.user = User.objects.get(id=self.base_user_id)
            self.client.force_login(self.user)

        if self.user and self.permission_required:
            perms = self.permission_required
            if isinstance(self.permission_required, str):
                perms = [self.permission_required]
            for perm in perms:
                self._set_user_perm(self.user, perm)

    def _set_user_perm(self, user: User, perm):
        if user.has_perm(perm):
            return
        user.user_permissions.add(self._get_perm_by_name(perm))

        # Delete the user permission cache
        del user._user_perm_cache
        del user._perm_cache

    def _get_perm_by_name(self, perm):
        app_label, perm_name = perm.split(".")

        return Permission.objects.get(
            codename=perm_name,
            content_type__app_label=app_label,
        )

    def _remove_user_perm(self, user: User, perm):
        if not user.has_perm(perm):
            return
        user.user_permissions.remove(self._get_perm_by_name(perm))
        # Delete the user permission cache
        del user._user_perm_cache
        del user._perm_cache

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
        response = self.client.post(url, data=data, follow=fetch_redirect_response)
        if redirect_url:
            # If a form errors, it won't redirect (chain is empty). So we can instantly debug
            #   redirect chain is only set when follow=True
            if hasattr(response, "context_data") and (
                (not fetch_redirect_response and response.status_code != 302)
                or (fetch_redirect_response and not response.redirect_chain)
            ):
                errors = response.context_data[self.form_context_name].errors.as_data()
                print(f"Form on {url} contained errors: \n {errors}")
            self.assertRedirects(response, redirect_url, fetch_redirect_response=fetch_redirect_response)
        else:
            self.assertEqual(response.status_code, 200, "Response was not a valid Http200 response")

        return response

    @suppress_warnings
    def assertPermissionDenied(self, data=None, url=None):
        """
        Assert that the view returns a permission denied
        :param data: Get data, defaults to an empty dict
        :param url: The url, defaults to self.get_base_url
        :return: Raises an AssertionError or does nothing
        """
        url = url or self.get_base_url()
        data = data or {}
        response = self.client.get(url, data=data)
        self.assertEqual(response.status_code, 403, "Access was not forbidden")

    def assertRequiresPermission(self, perm=None, data=None, url=None):
        """Asserts that the given permission name is required for this view
        :param data: URL data
        :param url: The url to be visited
        :param perm: The perm that needs to be validated
        """
        assert not self.user.is_superuser
        perm = perm or self.permission_required
        self._remove_user_perm(self.user, perm)
        self.assertPermissionDenied(data=data, url=url)

        self._set_user_perm(self.user, perm)
        self.assertValidGetResponse(data=data, url=url)

    @staticmethod
    def assertHasMessage(response, level=None, text=None):
        """
        Assert that the response contains a specific message
        :param response: The response object
        :param level: The level of the message (messages.SUCCESS/ERROR or custom...)
        :param text: (part of) the message string that it should contain
        :param print_all: prints all messages encountered useful to trace errors if present
        :return: Raises AssertionError if not asserted
        """
        # Update the level with the constant if the name of such a constant is given
        level = getattr(msg_constants, str(level), level)

        for message in response.context["messages"]:
            if message.level == level or level is None:
                if text is None or str(text) in message.message:
                    return

        if level or text:
            msg = "There was no message for the given criteria:"
            if level:
                msg += f" level: '{level}'"
            if text:
                msg += f" text: '{text}'"
            msg += ". The following messages were found instead: "
            for message in response.context["messages"]:
                msg += f"{message.level}: {message.message}, "
        else:
            msg = "There was no message"

        raise AssertionError(msg)


class TestMixinMixin:
    mixin_class = None
    base_user_id = None
    pre_inherit_classes = []
    view = None

    def _build_get_response(self, url=None, url_kwargs=None, save_view=True, user=None, post_inherit_class=None):
        """
        Constructs a get response through a temporary view that inheirts the Testcases mixin class
        :param url: The url path
        :param url_kwargs: Keyword arguments in the path as normally defined in the url path (e.g. object_id)
        :param save_view: Whether the view should be saved as self.view
        :param user: The user instace requesting the page. Defaults to user with id defined in self.base_user_id
        :return: The response instance
        """
        url = url or self.get_base_url()
        url_kwargs = url_kwargs or self.get_base_url_kwargs()

        request = RequestFactory().get(url)
        self._imitiate_request_middleware(request, user=user)

        view = self.get_as_full_view_class(post_inherit_class=post_inherit_class)()
        view.setup(request, **url_kwargs)
        response = view.dispatch(request, **url_kwargs)

        if save_view:
            self.view = view

        return response

    def _imitiate_request_middleware(self, request, user=None):
        if user is not None:
            request.user = user
        elif self.base_user_id:
            request.user = User.objects.get(id=self.base_user_id)

    def get_base_url(self):
        return ""

    def get_base_url_kwargs(self):
        """Constructs the url kwargs default values for each check"""
        return {}

    def get_as_full_view_class(self, post_inherit_class=None):
        """
        Returns a class implementing the mixin class that needs to be tested
        :param post_inherit_class: Class added after the list of required classes.
        This can be used to imitate any super logic that the mixin might need to be able to catch
        :return: A view class implementing the mixin for testing along with the pre_inherited classes
        """
        classes = self.pre_inherit_classes + [self.mixin_class]

        if post_inherit_class is not None:
            classes.append(post_inherit_class)

        class BaseMixinTestView:
            """This class returns a default response indicating the mixin has been handled"""

            def dispatch(self, request, *args, **kwargs):
                return HttpResponse("test successful")

        class MixinTestView(*classes, BaseMixinTestView, TemplateView):
            #
            pass

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

    def assertResponseSuccessful(self, response):
        if response.status_code != 200:
            raise AssertionError(f"Response was not successful. It returned code {response.status_code} instead.")
        if response.content != b"test successful":
            # HttpResponse content property is in byte form
            raise AssertionError(f"Response was not successful. It returned unexpected html content")
