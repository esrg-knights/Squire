from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from committees.account_pages.views import *


class AssociationGroupAccountTestCase(TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "inventory/test_ownership"]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(id=100)
        self.client.force_login(self.user)

        self.base_url = reverse("account:inventory:member_items")

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupAccountView, AccountViewMixin))
        self.assertTrue(issubclass(AssociationGroupAccountView, PermissionRequiredMixin))
        self.assertEqual(
            AssociationGroupAccountView.template_name, "committees/account_pages/account_group_overview.html"
        )
        self.assertEqual(
            AssociationGroupAccountView.permission_required, "membership_file.can_view_membership_information_self"
        )
