from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory

from core.models import ExtendedUser as User
from membership_file.util import membership_required


##################################################################################
# Test the Membership File Decorators
# @since 16 MAR 2020
##################################################################################

# Tests whether some decorator (with some settings) properly loads or
# redirects to some page requested by some user
def test_decorator(test, decorator, decorator_params={}, request_url="/some_url", view=None,
        factory=None, user=None, member=None, redirect_url=None):
    if factory is None:
        factory = RequestFactory()

    if user is None:
        user = AnonymousUser()

    if decorator_params is None:
        # Apply the decorator without parameters
        @decorator
        def some_view(request):
            if view is None:
                return HttpResponse()
            return view(request)
    else:
        # If no parameters are passed, also test @decorator syntax (note the absense of brackets after the decorator)
        if not decorator_params:
            test_decorator(test, decorator, decorator_params=None, request_url=request_url, view=view,
                factory=factory, user=user, member=member, redirect_url=redirect_url)

        # Apply the decorator with the given parameters
        @decorator(**decorator_params)
        def some_view(request):
            if view is None:
                return HttpResponse()
            return view(request)

    # Make the request
    # Set custom values for non-activated middleware
    request = factory.get(request_url)
    request.user = user
    request.member = member
    response = some_view(request)

    if redirect_url is not None:
        # Should be redirected
        test.assertEqual(response.status_code, 302)
        test.assertEqual(response.url, redirect_url)
        pass
    else:
        # Should not be redirected
        test.assertEqual(response.status_code, 200)

    # Return the response in case the calling method wants to test more
    return response

#########################################################################################

# Tests the membership_required decorator
class MembershipRequiredDecoratorTest(TestCase):
    fixtures = ['test_users.json', 'test_members.json']

    def setUp(self):
        self.member_user = User.objects.filter(username="test_member").first()
        self.member = self.member_user.member
        self.nonmember_user = User.objects.filter(username="test_user").first()
        self.factory = RequestFactory()

    # Tests if members are not redirected to the fail page
    def test_no_redirect(self):
        test_decorator(self, membership_required, user=self.member_user, member=self.member, factory=self.factory)

    # Tests if non-members are redirected to the fail page
    def test_redirect(self):
        test_decorator(self, membership_required, user=self.nonmember_user,
            redirect_url=settings.MEMBERSHIP_FAIL_URL, factory=self.factory)

        # Tests alternative redirects
        test_decorator(self, membership_required, decorator_params={
                'fail_url': "/fail_url"
            },
            user=self.nonmember_user, redirect_url="/fail_url", factory=self.factory)

    # Tests if non-logged in users are redirected to the login page
    def test_redirect_not_logged_in(self):
        test_decorator(self, membership_required, request_url="/rand",
            redirect_url=f"{settings.LOGIN_URL}?{REDIRECT_FIELD_NAME}=/rand", factory=self.factory)

        test_decorator(self, membership_required, request_url="/rand", decorator_params={
                'fail_url':             "/fail_url",
                'redirect_field_name':  "redirect_field_name",
                'login_url':            "/login_url",
            },
            redirect_url=f"/login_url?redirect_field_name=/rand", factory=self.factory)
