from django.contrib.auth.models import Permission
from django.test import TestCase

from utils.auth_utils import get_perm_from_name


class UtilMethodsTestCase(TestCase):
    def test_get_perm_from_name(self):
        perm = get_perm_from_name("auth.change_user")
        self.assertIsInstance(perm, Permission)
        self.assertEqual(perm.codename, "change_user")
