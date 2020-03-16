from django.test import TestCase
from django.test import Client
from django.conf import settings

from enum import Enum

from core.models import ExtendedUser as User

##################################################################################
# Utility Methods for testcases
# @since 15 AUG 2019
##################################################################################

# An enumeration that allows comparison
# See: https://docs.python.org/3/library/enum.html#orderedenum
class OrderedEnum(Enum):
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented
    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented
    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

class PermissionLevel(OrderedEnum):
    LEVEL_PUBLIC = 1
    LEVEL_USER = 2
    LEVEL_ADMIN = 3

#
# Checks whether a given url can be accessed with a given HTTP Method by a user with a given permissionLevel
# 
# @param test A testcase instance used to make Assertions
# @param url URL to make the request to
# @param httpMethod HTTP Method to make the request with E.g. get, post, put, etc. 
# @param permissionLevel Which type of user should be able to access the page
# @param user The user to use in the request (or empty if a new one should be created)
# @param redirectUrl The Url to redirect to
# @param data Additional data to pass to the request
# 
# @throws AssertionError iff a user of the given permission level can NOT access the given url using the given HTTP method
#
def checkAccessPermissions(test: TestCase, url: str, httpMethod: str, permissionLevel: PermissionLevel,
        user: User = None, redirectUrl: str = "", data: dict = {}) -> None:
    client = Client()
    
    # Ensure the correct type of user makes the request
    if permissionLevel == PermissionLevel.LEVEL_USER:
        if user is None:
            user = User.objects.get(username='test_user')
        elif user.is_superuser:
            user.is_superuser = False
            User.save(user)
    elif permissionLevel == PermissionLevel.LEVEL_ADMIN:
        if user is None:
            user = User.objects.get(username='test_admin')
        elif not user.is_superuser:
            user.is_superuser = True
            User.save(user)

    # Ensure the correct user is logged in
    if user:
        client.force_login(user)

    # Issue a HTTP request.
    response = getattr(client, httpMethod)(url, data=data, follow=(bool(redirectUrl)), secure=True)

    # Ensure that a 200 OK response is received
    test.assertEqual(response.status_code, 200)

    # Ensure we were redirected to the correct page
    if redirectUrl:
        # Ensure a redirection to the expected URL took place
        test.assertRedirects(response, redirectUrl)

    # Check if we get redirected to the login page if not logged in, but a login is required
    # Skip this check if we expect a different redirect (which was already checked earlier)
    if permissionLevel <= PermissionLevel.LEVEL_PUBLIC or redirectUrl:
        return
    
    # Ensure the client is not logged in
    client.logout()

    # Issue a HTTP request.
    response = getattr(client, httpMethod)(url, data=data, follow=True, secure=True)

    # Ensure that a 200 OK response is received
    test.assertEqual(response.status_code, 200)

    # Ensure a redirection to the login page took place
    test.assertRedirects(response, '{0}?next={1}'.format(settings.LOGIN_URL, url))

    # Check if we get redirected to the login page if we're not an admin
    if permissionLevel <= PermissionLevel.LEVEL_USER:
        return

    # Ensure the client is not logged in
    client.force_login(user)

    # Issue a HTTP request.
    response = getattr(client, httpMethod)(url, data=data, follow=True, secure=True)

    # Ensure that a 200 OK response is received
    test.assertEqual(response.status_code, 200)

    # Ensure a redirection to the login page took place
    test.assertRedirects(response, '{0}?next={1}'.format(settings.LOGIN_URL, url))
