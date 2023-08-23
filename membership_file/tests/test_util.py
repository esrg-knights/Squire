from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.http.response import HttpResponseRedirect

from utils.testing.view_test_utils import TestMixinMixin

from membership_file.exceptions import UserIsNotCurrentMember
from membership_file.util import user_is_current_member, MembershipRequiredMixin, get_member_from_user


class TestUserIsCurrentMember(TestCase):
    fixtures = ["test_users", "test_members.json"]

    def test_no_member_linked(self):
        self.assertFalse(user_is_current_member(User.objects.create()))

    def test_no_active_membership(self):
        self.assertFalse(user_is_current_member(User.objects.get(id=3)))

    def test_active_mebership(self):
        self.assertTrue(user_is_current_member(User.objects.get(id=100)))


class MembershipRequiredMixinTestCase(TestMixinMixin, TestCase):
    fixtures = ["test_users", "test_members.json"]
    mixin_class = MembershipRequiredMixin
    requires_active_membership = None  # The state of requires_active_membership on the class. None = default

    def _imitiate_request_middleware(self, request, **kwargs):
        super(MembershipRequiredMixinTestCase, self)._imitiate_request_middleware(request, **kwargs)
        request.member = get_member_from_user(request.user)

    def get_as_full_view_class(self, **kwargs):
        klass = super(MembershipRequiredMixinTestCase, self).get_as_full_view_class(**kwargs)
        if self.requires_active_membership is not None:
            klass.requires_active_membership = self.requires_active_membership
        return klass

    def test_no_user(self):
        """Test that non-logged in users are redirected to a login page"""
        response = self._build_get_response("member_area/", user=AnonymousUser())
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response["Location"], f"{settings.LOGIN_URL}?next=/member_area")

    def test_no_member(self):
        """Test that non-members are lead to an access denied page"""
        with self.assertRaises(UserIsNotCurrentMember):
            self._build_get_response("member_area/", user=User.objects.get(id=1))

    def test_active_member_granted(self):
        response = self._build_get_response("member_area/", user=User.objects.get(id=100))
        self.assertResponseSuccessful(response)

    def test_inactive_member_denied(self):
        """Test that non-members are lead to an access denied page"""
        with self.assertRaises(UserIsNotCurrentMember):
            self._build_get_response("member_area/", user=User.objects.get(id=3))

    def test_inactive_member_granted_on_requires_active_membership_is_false(self):
        self.requires_active_membership = False
        response = self._build_get_response("member_area/", user=User.objects.get(id=3))
        self.assertResponseSuccessful(response)
