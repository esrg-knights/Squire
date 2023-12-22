from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.http.response import HttpResponseRedirect
from django.test import TestCase

from membership_file.exceptions import UserIsNotCurrentMember
from membership_file.models import Member
from membership_file.util import (
    LinkAccountTokenGenerator,
    user_is_current_member,
    MembershipRequiredMixin,
    get_member_from_user,
)
from utils.testing.view_test_utils import TestMixinMixin

User = get_user_model()


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


class LinkAccountTokenGeneratorTestCase(TestCase):
    """Tests for LinkAccountTokenGenerator"""

    def test_key_salt(self):
        """Key salt should be different from Django's PasswordTokenGenerator. Otherwise tokens can be interchangeable."""
        self.assertNotEqual(LinkAccountTokenGenerator.key_salt, PasswordResetTokenGenerator.key_salt)

    def test_hash(self):
        """Tests hashing; data in the hash should ensure the token expires once used"""
        user = User.objects.create(username="user")
        member = Member.objects.create(
            user=user, first_name="Member", last_name="Rembem", legal_name="Member Rembem", email="member@example.com"
        )
        generator = LinkAccountTokenGenerator()
        hash = generator._make_hash_value(member, 999)
        # The following two values are guaranteed to change upon an account link (this invalidates the token)
        self.assertIn(str(user.pk), hash)
        self.assertIn(str(member.last_updated_date.replace(microsecond=0, tzinfo=None)), hash)
        # The following values uniquely identify the member
        self.assertIn(str(member.pk), hash)
        self.assertIn(member.email, hash)
        # Timestamp should also be included
        self.assertIn("999", hash)
