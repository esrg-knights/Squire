from django.test import TestCase, override_settings
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, AnonymousUser

from core.backends import BaseUserBackend
from membership_file.models import Member

User = get_user_model()

##################################################################################
# Test cases for custom backends
# @since 18 NOV 2020
##################################################################################

# Tests the authentication backend responsible for default permissions
class BaseBackendTest(TestCase):

    @override_settings(MEMBERSHIP_FILE_EXPORT_PATH=None)
    def test_default_permissions(self):
        # Override default permissions with test permissions
        BaseUserBackend.base_permissions = ('core.add_presetimage',)
        BaseUserBackend.logged_in_user_permissions = ('core.change_presetimage',)
        BaseUserBackend.member_permissions = ('core.delete_presetimage',)

        # Anonymous user permissions
        user = AnonymousUser()
        self.assertTrue(user.has_perm('core.add_presetimage'))
        self.assertFalse(user.has_perm('core.change_presetimage'))
        self.assertFalse(user.has_perm('core.delete_presetimage'))

        # Logged in user permissions
        user = User.objects.create_user(username='user', password='password')
        self.assertTrue(user.has_perm('core.change_presetimage'))
        self.assertTrue(user.has_perm('core.change_presetimage'))
        self.assertFalse(user.has_perm('core.delete_presetimage'))

        # Member permissions
        member = Member.objects.create(**{
            "user": user,
            "first_name": "User",
            "last_name": "Member",
            "date_of_birth": "1970-01-01",
            "email": "usermember@example.com",
            "street": "street",
            "house_number": "1",
            "city": "city",
            "country": "country",
            "member_since": "1970-01-01",
            "educational_institution": "school",
        })
        self.assertTrue(user.has_perm('core.change_presetimage'))
        self.assertTrue(user.has_perm('core.change_presetimage'))
        self.assertTrue(user.has_perm('core.delete_presetimage'))
