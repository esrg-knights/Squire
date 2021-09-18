from django.test import TestCase
from django.conf import settings
from django.urls.base import reverse
from dynamic_preferences.registries import global_preferences_registry

from core.forms import LoginForm, RegisterForm
from core.models import ExtendedUser as User
from core.tests.util import check_http_response, TestPublicUser, TestAccountUser, suppress_warnings

##################################################################################
# Test cases for core
# @since 15 AUG 2019
##################################################################################

# Tests whether front-end pages can be accessed
class FrontEndTest(TestCase):
    fixtures = TestAccountUser.get_fixtures()

    # Tests if the login page can be accessed
    def test_login(self):
        check_http_response(self, settings.LOGIN_URL, 'get', TestPublicUser)

    # Tests if the logout-success page can be accessed
    def test_logout_success(self):
        check_http_response(self, settings.LOGOUT_REDIRECT_URL, 'get', TestPublicUser)

    # Tests if the logout-success page can be accessed if logged in
    def test_logout_success_when_logged_in(self):
        check_http_response(self, settings.LOGOUT_REDIRECT_URL, 'get', TestAccountUser,
            redirect_url=settings.LOGOUT_REDIRECT_URL)

    # Tests if the account page can be accessed
    def test_account(self):
        check_http_response(self, '/account', 'get', TestAccountUser)

    # Tests if the logout page can be accessed if not logged in
    def test_logout_redirect(self):
        check_http_response(self, settings.LOGOUT_URL, 'get', TestPublicUser,
            redirect_url=settings.LOGOUT_REDIRECT_URL)

    # Tests if the register-page can be accessed
    def test_register(self):
        check_http_response(self, '/register', 'get', TestPublicUser)

    # Tests if the register-success page can be accessed
    def test_register_success(self):
        check_http_response(self, '/register/success', 'get', TestPublicUser)

    # Tests if the newsletter URL is being rendered properly
    @suppress_warnings
    def test_newsletter(self):
        global_preferences = global_preferences_registry.manager()

        # Disable share URL
        global_preferences['newsletter__share_link'] = ""
        check_http_response(self, reverse('core:newsletters'), 'get', TestAccountUser, response_status=404)

        # Enable share URL
        global_preferences['newsletter__share_link'] = "https://www.example.com"
        res = check_http_response(self, reverse('core:newsletters'), 'get', TestAccountUser)
        self.assertContains(res, "https://www.example.com")

    # The "Newsletters" tab should not be present in the base template if there is no share url
    def test_newsletter_link_in_base_template(self):
        global_preferences = global_preferences_registry.manager()

        # Disable share URL
        global_preferences['newsletter__share_link'] = ""
        res = check_http_response(self, '/', 'get', TestAccountUser)
        self.assertNotContains(res, reverse('core:newsletters'))

        # Enable share URL
        global_preferences['newsletter__share_link'] = "https://www.example.com"
        res = check_http_response(self, '/', 'get', TestAccountUser)
        self.assertContains(res, reverse('core:newsletters'))


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


# Tests the register form
class RegisterFormTest(TestCase):
    def setUp(self):
        # Called each time before a testcase runs
        # Set up data for each test.
        self.user = User.objects.create_user(username="schaduwbestuur", password="bestaatniet", email='rva@example.com')
        User.save(self.user)

    # Test if the user can register if everything is correct
    def test_form_correct(self):
        form_data = {
            'username': 'schaduwkandi',
            'password1': 'bestaatookniet',
            'password2': 'bestaatookniet',
            'email': 'kandi@example.com',
            'real_name': 'wijbestaanniet',
        }
        form = RegisterForm(data=form_data)

        # Data that was entered is correct
        self.assertTrue(form.is_valid())

        # Ensure the correct object is returned (but not saved)
        user = form.save(commit=False)
        self.assertIsNotNone(user)
        self.assertEquals(user.email, 'kandi@example.com')
        self.assertTrue(user.check_password('bestaatookniet'))
        self.assertEqual(user.first_name, 'wijbestaanniet')

        user = User.objects.filter(username='schaduwkandi').first()
        self.assertIsNone(user)

        # Ensure the correct data is saved
        form.save(commit=True)
        user = User.objects.filter(username='schaduwkandi').first()
        self.assertIsNotNone(user)
        self.assertEquals(user.email, 'kandi@example.com')
        self.assertTrue(user.check_password('bestaatookniet'))
        self.assertEqual(user.first_name, 'wijbestaanniet')

    # Test if a registering fails if required fields are missing
    def test_form_fields_missing(self):
        form_data = {
            'real_name': 'empty',
        }
        form = RegisterForm(data=form_data)

        # Data that was entered is incorrect
        self.assertFalse(form.is_valid())

        # Ensure that only one error was given per missing field
        self.assertTrue(form.has_error('username'))
        self.assertEqual(len(form.errors.as_data()['username']), 1)
        self.assertTrue(form.has_error('password1'))
        self.assertEqual(len(form.errors.as_data()['password1']), 1)
        self.assertTrue(form.has_error('password2'))
        self.assertEqual(len(form.errors.as_data()['password2']), 1)
        self.assertTrue(form.has_error('email'))
        self.assertEqual(len(form.errors.as_data()['email']), 1)
        self.assertEqual(len(form.errors.as_data()), 4)

    # Test if a registering fails if the two passwords do not match
    def test_form_nonmatching_password(self):
        form_data = {
            'username': 'schaduwkandi',
            'password1': 'bestaatookniet',
            'password2': 'nomatch',
            'email': 'kandi@example.com',
            'real_name': 'wijbestaanniet',
        }
        form = RegisterForm(data=form_data)

        # Data that was entered is incorrect
        self.assertFalse(form.is_valid())

        # Ensure that only one error was given
        self.assertTrue(form.has_error('password2'))
        self.assertEqual(len(form.errors.as_data()['password2']), 1)

    # Test if a registering fails if username or email was already chosen by another user
    def test_form_duplicate_field(self):
        form_data = {
            'username': 'schaduwbestuur',
            'password1': 'secret',
            'password2': 'secret',
            'email': 'rva@example.com',
            'real_name': 'wijbestaanniet',
        }
        form = RegisterForm(data=form_data)

        # Data that was entered is incorrect
        self.assertFalse(form.is_valid())

        # Ensure that only one error was given
        self.assertTrue(form.has_error('username'))
        self.assertEqual(len(form.errors.as_data()['username']), 1)
        self.assertTrue(form.has_error('email'))
        self.assertEqual(len(form.errors.as_data()['email']), 1)


# Tests the registerForm view
class RegisterFormViewTest(TestCase):
    fixtures = TestAccountUser.get_fixtures()

    # Tests if redirected when form data was entered correctly
    def test_success_redirect(self):
        form_data = {
            'username': 'username',
            'password1': 'thisactuallyneedstobeagoodpassword',
            'password2': 'thisactuallyneedstobeagoodpassword',
            'email': 'email@example.com',
            'real_name': "My Real name",
        }
        check_http_response(self, '/register', 'post', TestPublicUser,
                redirect_url='/register/success', data=form_data)

        user = User.objects.filter(username='username').first()
        self.assertIsNotNone(user)
        self.assertEquals(user.email, 'email@example.com')
        self.assertTrue(user.check_password('thisactuallyneedstobeagoodpassword'))
        self.assertEqual(user.first_name, 'My Real name')

    # Tests if not redirected when form data was entered incorrectly
    def test_fail_form_enter_no_real_name(self):
        form_data = {
            'username': 'username',
            'password1': 'thisactuallyneedstobeagoodpassword', # Real name not passed
            'password2': 'thisactuallyneedstobeagoodpassword',
            'email': 'email@example.com',
        }
        check_http_response(self, '/register', 'post', TestPublicUser, data=form_data)

        user = User.objects.filter(username='username').first()
        self.assertIsNone(user)

    # Tests if not redirected when form data was entered incorrectly
    def test_fail_form_enter(self):
        form_data = {
            'username': 'username',
            'password1': 'password', # Password too easy so should fail
            'password2': 'password',
            'email': 'email@example.com',
            'real_name': "My Real name",
        }
        check_http_response(self, '/register', 'post', TestPublicUser, data=form_data)

        user = User.objects.filter(username='username').first()
        self.assertIsNone(user)
