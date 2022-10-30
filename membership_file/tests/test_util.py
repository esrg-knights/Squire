from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from membership_file.util import user_is_current_member


class TestUserIsCurrentMember(TestCase):
    fixtures = ['test_users', 'test_members.json']

    def test_no_member_linked(self):
        self.assertFalse(user_is_current_member(User.objects.create()))

    def test_no_active_membership(self):
        self.assertFalse(user_is_current_member(User.objects.get(id=3)))

    def test_active_mebership(self):
        self.assertTrue(user_is_current_member(User.objects.get(id=100)))
