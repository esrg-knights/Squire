from collections import Collection
import logging
from functools import wraps

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from dynamic_preferences.registries import global_preferences_registry

from core.models import ExtendedUser as User
from core.util import get_permission_objects_from_string


##################################################################################
# Utility Methods for testcases
# @since 15 AUG 2019
##################################################################################

class TestSquireUser():
    instance = None
    fixtures = []

    @classmethod
    def get_fixtures(cls):
        return cls.fixtures

    @classmethod
    def get_user_object(cls):
        user = AnonymousUser()
        if cls.instance is not None:
            user = User.objects.get(username=cls.instance)
        return user

class TestPublicUser(TestSquireUser):
    pass

class TestAccountUser(TestPublicUser):
    instance = 'test_user'

    @classmethod
    def get_fixtures(cls):
        return super().get_fixtures() + ['test_users.json']


def check_http_response(test: TestCase, url: str, http_method: str, squire_user: TestSquireUser,
        permissions: Collection = [], response_status: int = 200, redirect_url: str = None,
        data: dict = {}, **kwargs):
    """
    Checks whether a given url can be accessed with a given HTTP Method by a
        given Squire User (e.g. account holders, anonymous users, etc.)

    :param test:            A testcase instance used to make Assertions
    :param url:             URL to make the request to
    :param http_method:     HTTP Method to make the request with E.g. get, post, put, ...
    :param squire_user:     The type of user that makes the request
    :param permissions:     Any permissions given to the user prior to making the request
    :param response_status: The expected response status
    :param redirect_url:    The expected url to be redirected to
    :param data:            Additional data to pass to the request

    :throws AssertionError: The user of the given type did not receive the expected response,
                                or was not redirected to the expected page
    :returns:               The response.
    """

    client = test.client
    user = squire_user.get_user_object()

    # Grant the user the required permissions, and log in if needed
    if not user.is_anonymous:
        client.force_login(user)
        user.user_permissions.add(*list(get_permission_objects_from_string(permissions)))
    elif permissions:
        # Anonymous users cannot be assigned Permissions directly. Use Django Dynamic Preferences instead.
        global_preferences = global_preferences_registry.manager()
        global_preferences['permissions__base_permissions'] = get_permission_objects_from_string(permissions)

    # Issue an HTTP request
    response = getattr(client, http_method)(url, data=data, follow=(redirect_url is not None), secure=True, **kwargs)

    # Ensure that the expected response is received
    test.assertEqual(response.status_code, response_status)

    # Ensure we were redirected to the expected page
    if redirect_url is not None:
        test.assertRedirects(response, redirect_url)

    # Reset state
    client.logout()
    return response


def check_http_response_with_login_redirect(test, url, http_method, **kwargs):
    """
    Tests whether an Squire Account User can access a given page, and whether someone without an
        account is redirected to the login page when accessing that same page.
        Method has otherwise the same parameters as check_http_response

    :throws AssertionError: The account holder could not access the page,
                                or the public user was not redirected to the login page.
    :returns:               A tuple of both responses (account user first).
    """
    return (
        check_http_response(test, url, http_method, squire_user=TestAccountUser,
            response_status=200, **kwargs),
        check_http_response(test, url, http_method, squire_user=TestPublicUser,
            response_status=200, redirect_url=(f"{settings.LOGIN_URL}?next={url}"), **kwargs)
    )


def suppress_warnings(function=None, logger_name='django.request'):
    """
    Decorator that surpresses Django-warnings when calling a function.
    Useful for testcases where warnings are triggered on purpose and only
    clutter the command prompt.
    Source: https://stackoverflow.com/a/46079090
    """
    def decorator(original_func):
        @wraps(original_func)
        def _wrapped_view(*args, **kwargs):
            # raise logging level to ERROR
            logger = logging.getLogger(logger_name)
            previous_logging_level = logger.getEffectiveLevel()
            logger.setLevel(logging.ERROR)

            # trigger original function that would throw warning
            original_func(*args, **kwargs)

            # lower logging level back to previous
            logger.setLevel(previous_logging_level)
        return _wrapped_view

    if function:
        return decorator(function)
    return decorator
