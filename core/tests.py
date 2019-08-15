from django.test import TestCase
from django.test import Client
from django.contrib.auth.models import User
from django.conf import settings
from .forms import LoginForm
from enum import Enum


##################################################################################
# Test cases for core
# @author E.M.A. Arts
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
# 
# @throws AssertionError iff a user of the given permission level can NOT access the given url using the given HTTP method
#
def checkAccessPermissions(test: TestCase, url: str, httpMethod: str, permissionLevel: PermissionLevel,
        redirectUrl: str = "", data: dict = {}) -> None:
    client = Client()
    
    # Ensure the correct type of user makes the request
    user = None
    if permissionLevel == PermissionLevel.LEVEL_USER:
        user = User.objects.create_user(username="username", password="username")
        User.save(user)
    elif permissionLevel == PermissionLevel.LEVEL_ADMIN:
        user = User.objects.create_superuser(username="admin", password="admin", email="")
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


# Tests whether front-end pages can be accessed
class FrontEndTest(TestCase):
    # Tests if the homepage can be accessed
    def test_homepage(self):
        checkAccessPermissions(self, '/', 'get', PermissionLevel.LEVEL_PUBLIC)

    # Tests if the login page can be accessed
    def test_login(self):
        checkAccessPermissions(self, settings.LOGIN_URL, 'get', PermissionLevel.LEVEL_PUBLIC)

    # Tests if the logout-success page can be accessed
    def test_logout_success(self):
        checkAccessPermissions(self, settings.LOGOUT_REDIRECT_URL, 'get', PermissionLevel.LEVEL_PUBLIC)
    
    # Tests if the logout-success page can be accessed if logged in
    def test_logout_success_when_logged_in(self):
        checkAccessPermissions(self, settings.LOGOUT_REDIRECT_URL, 'get', PermissionLevel.LEVEL_USER, redirectUrl=settings.LOGOUT_REDIRECT_URL)

    # Tests if the account page can be accessed
    def test_account(self):
        checkAccessPermissions(self, '/account', 'get', PermissionLevel.LEVEL_USER)

    # Tests if the logout page can be accessed if not logged in
    def test_logout_redirect(self):
        checkAccessPermissions(self, settings.LOGOUT_URL, 'get', PermissionLevel.LEVEL_PUBLIC, redirectUrl=settings.LOGOUT_REDIRECT_URL)


# Tests the login form
class LoginFormTest(TestCase):
    def setUp(self):
        # Called each time before a testcase runs
        # Set up data for each test.
        self.user = User.objects.create_user(username="its-a-me", password="mario")
        User.save(self.user)

    # Test if a login is allowed if the username-password pair are correct
    def test_form_correct(self):
        form_data = {
            'username': 'its-a-me',
            'password': 'mario',        
        }
        form = LoginForm(data=form_data)
        # Data that was entered is correct
        self.assertTrue(form.is_valid())
    
    # Test if a login is disallowed if the username-password pair are incorrect
    def test_form_incorrect(self):
        form_data = {
            'username': 'its-a-me',
            'password': 'luigi',        
        }
        form = LoginForm(data=form_data)
        
        # Data that was entered is incorrect
        self.assertFalse(form.is_valid())

        # Ensure that only one (general) error was given
        self.assertEqual(len(form.errors.as_data()), 1)
        self.assertEqual(len(form.non_field_errors().as_data()), 1)
        self.assertEqual(form.non_field_errors().as_data()[0].code, 'ERROR_INVALID_LOGIN')
        
    # Test if a login is disallowed if the username is missing
    def test_form_username_missing(self):
        form_data = {
            'password': 'wario',        
        }
        form = LoginForm(data=form_data)
        
        # Data that was entered is incorrect
        self.assertFalse(form.is_valid())
        
        # Ensure that only one error was given
        self.assertTrue(form.has_error('username'))
        self.assertEqual(len(form.errors.as_data()), 1)