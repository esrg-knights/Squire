from django.contrib import messages
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.views.generic import FormView

from utils.testing.view_test_utils import ViewValidityMixin
from user_interaction.accountcollective import AccountViewMixin

from inventory.forms import *
from inventory.models import Ownership
from inventory.account_pages.views import *
from inventory.views import OwnershipMixin


class TestMemberItemsOverview(TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "inventory/test_ownership"]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(id=100)
        self.client.force_login(self.user)

        self.base_url = reverse("account:inventory:member_items")
        # self.base_response = self.client.get(self.base_url, data={})

    def test_class(self):
        self.assertTrue(issubclass(MemberItemsOverview, AccountViewMixin))
        self.assertEqual(
            MemberItemsOverview.template_name, "inventory/account_pages/inventory/membership_inventory.html"
        )
        self.assertEqual(MemberItemsOverview.context_object_name, "ownerships")

    def test_member_items_successful(self):
        response = self.client.get(self.base_url, data={})
        self.assertEqual(response.status_code, 200)

    def test_template_context(self):
        response = self.client.get(self.base_url, data={})
        context = response.context

        self.assertEqual(context["ownerships"].first().id, 1)
        self.assertEqual(context["ownerships_history"].first().id, 2)


class TestMemberItemRemovalFormView(ViewValidityMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "inventory/test_ownership"]
    base_user_id = 100

    def setUp(self):
        self.ownership = Ownership.objects.get(id=1)
        super(TestMemberItemRemovalFormView, self).setUp()

    def get_base_url(self, ownership_id=None):
        ownership_id = ownership_id or self.ownership.id
        return reverse(
            "account:inventory:member_take_home",
            kwargs={
                "ownership_id": ownership_id,
            },
        )

    def test_class(self):
        self.assertTrue(issubclass(MemberItemRemovalFormView, FormView))
        self.assertTrue(issubclass(MemberItemRemovalFormView, OwnershipMixin))
        self.assertTrue(issubclass(MemberItemRemovalFormView, AccountViewMixin))
        self.assertEqual(MemberItemRemovalFormView.form_class, OwnershipRemovalForm)
        self.assertEqual(
            MemberItemRemovalFormView.template_name, "inventory/account_pages/inventory/membership_take_home.html"
        )

    def test_get_successful(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_post_successful(self):
        response = self.client.post(self.get_base_url(), data={}, follow=True)
        self.assertRedirects(response, reverse("account:inventory:member_items"))
        msg = "{item} has been marked as taken home".format(item=self.ownership.content_object)
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)

    def test_post_invalid_form(self):
        # Get an item that causes the form to fail. This form should automatically forward when failing
        # as the user can not adjust form data to fix it
        response = self.client.post(self.get_base_url(ownership_id=2), data={}, follow=True)
        self.assertRedirects(response, reverse("account:inventory:member_items"))
        self.assertHasMessage(response, level=messages.ERROR)


class TestMemberItemLoanFormView(ViewValidityMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "inventory/test_ownership"]
    base_user_id = 100

    def setUp(self):
        self.ownership = Ownership.objects.get(id=2)
        super(TestMemberItemLoanFormView, self).setUp()

    def get_base_url(self, ownership_id=None):
        ownership_id = ownership_id or self.ownership.id
        return reverse(
            "account:inventory:member_loan_out",
            kwargs={
                "ownership_id": ownership_id,
            },
        )

    def test_class(self):
        self.assertTrue(issubclass(MemberItemLoanFormView, FormView))
        self.assertTrue(issubclass(MemberItemLoanFormView, OwnershipMixin))
        self.assertTrue(issubclass(MemberItemRemovalFormView, AccountViewMixin))
        self.assertEqual(MemberItemLoanFormView.form_class, OwnershipActivationForm)
        self.assertEqual(
            MemberItemLoanFormView.template_name, "inventory/account_pages/inventory/membership_loan_out.html"
        )

    def test_get_successful(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_post_successful(self):
        response = self.client.post(self.get_base_url(), data={}, follow=True)
        self.assertRedirects(response, reverse("account:inventory:member_items"))
        msg = "{item} has been marked as stored at the Knights".format(item=self.ownership.content_object)
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)

    def test_post_invalid_form(self):
        # Get an item that causes the form to fail. This form should automatically forward when failing
        # as the user can not adjust form data to fix it
        response = self.client.post(self.get_base_url(ownership_id=1), data={}, follow=True)
        self.assertRedirects(response, reverse("account:inventory:member_items"))
        self.assertHasMessage(response, level=messages.ERROR)


class TestMemberOwnershipAlterView(ViewValidityMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "inventory/test_ownership"]
    base_user_id = 100

    def setUp(self):
        self.ownership = Ownership.objects.get(id=2)
        super(TestMemberOwnershipAlterView, self).setUp()

    def get_base_url(self, ownership_id=None):
        ownership_id = ownership_id or self.ownership.id
        return reverse(
            "account:inventory:owner_link_edit",
            kwargs={
                "ownership_id": ownership_id,
            },
        )

    def test_class(self):
        self.assertTrue(issubclass(MemberItemLoanFormView, FormView))
        self.assertEqual(MemberOwnershipAlterView.form_class, OwnershipNoteForm)
        self.assertEqual(
            MemberOwnershipAlterView.template_name, "inventory/account_pages/inventory/membership_adjust_note.html"
        )

    def test_get_successful(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_post_successful(self):
        response = self.client.post(self.get_base_url(), data={}, follow=True)
        self.assertRedirects(response, reverse("account:inventory:member_items"))
        msg = "Your version of {item} has been updated".format(item=self.ownership.content_object)
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)
