import datetime


from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group, User
from django.http import HttpResponse
from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse
from django.views.generic.base import View

from core.util import suppress_warnings
from utils.testing.view_test_utils import ViewValidityMixin, TestMixinMixin

from inventory.forms import *
from inventory.models import Ownership, BoardGame
from inventory.views import *


class TestMemberItemsView(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(id=2)
        self.client.force_login(self.user)

        self.base_url = reverse('inventory:member_items')
        # self.base_response = self.client.get(self.base_url, data={})

    @suppress_warnings  # Testing 403 raises a warning that 403 was triggered
    def test_member_items_validity(self):
        response = self.client.get(self.base_url, data={})
        self.assertEqual(response.status_code, 200)

        # Test a user taht is not a member
        self.client.force_login(User.objects.get(id=3))
        response = self.client.get(self.base_url, data={})
        self.assertEqual(response.status_code, 403)

    def test_template_context(self):
        response  = self.client.get(self.base_url, data={})
        context = response.context

        self.assertEqual(context['ownerships'].first().id, 1)
        self.assertEqual(context['ownerships_history'].first().id, 2)


class TestOwnershipMixin(TestMixinMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    mixin_class = OwnershipMixin
    base_user_id = 2

    def setUp(self):
        self.ownership = Ownership.objects.get(id=2)
        super(TestOwnershipMixin, self).setUp()

    def get_base_url_kwargs(self):
        return {'ownership_id': self.ownership.id}

    def test_get_successful(self):
        response = self._build_get_response()
        self.assertEqual(response.status_code, 200)

    def test_context_data(self):
        self._build_get_response(save_view=True)
        context = self.view.get_context_data()
        self.assertIn('ownership', context.keys())
        self.assertEqual(context['ownership'], self.ownership)

    def test_get_no_access(self):
        # A new ownership that is not owned by the current user (member_id=1)
        not_my_ownership = Ownership.objects.create(
            member_id=3,
            content_object=BoardGame.objects.last()
        )
        self.assertRaises403(url_kwargs={'ownership_id': not_my_ownership.id})

    def test_get_non_existent(self):
        self.assertRaises404(url_kwargs={'ownership_id': 99})


class TestMemberItemRemovalFormView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    base_user_id = 2

    def setUp(self):
        self.ownership = Ownership.objects.get(id=1)
        super(TestMemberItemRemovalFormView, self).setUp()

    def get_base_url(self, ownership_id=None):
        ownership_id = ownership_id or self.ownership.id
        return reverse('inventory:member_take_home', kwargs={'ownership_id':ownership_id,})

    def test_class(self):
        self.assertTrue(issubclass(MemberItemRemovalFormView, FormView))
        self.assertEqual(MemberItemRemovalFormView.form_class, OwnershipRemovalForm)
        self.assertEqual(MemberItemRemovalFormView.template_name, "inventory/membership_take_home.html")

    def test_get_successful(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_post_successful(self):
        response = self.client.post(self.get_base_url(), data={}, follow=True)
        self.assertRedirects(response, reverse('inventory:member_items'))
        msg = "{item} has been marked as taken home".format(item=self.ownership.content_object)
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)

    def test_post_invalid_form(self):
        # Get an item that causes the form to fail. This form should automatically forward when failing
        # as the user can not adjust form data to fix it
        response = self.client.post(self.get_base_url(ownership_id=2), data={}, follow=True)
        self.assertRedirects(response, reverse('inventory:member_items'))
        self.assertHasMessage(response, level=messages.ERROR)


class TestMemberItemLoanFormView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    base_user_id = 2

    def setUp(self):
        self.ownership = Ownership.objects.get(id=2)
        super(TestMemberItemLoanFormView, self).setUp()

    def get_base_url(self, ownership_id=None):
        ownership_id = ownership_id or self.ownership.id
        return reverse('inventory:member_loan_out', kwargs={'ownership_id':ownership_id,})

    def test_class(self):
        self.assertTrue(issubclass(MemberItemLoanFormView, FormView))
        self.assertEqual(MemberItemLoanFormView.form_class, OwnershipActivationForm)
        self.assertEqual(MemberItemLoanFormView.template_name, "inventory/membership_loan_out.html")

    def test_get_successful(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_post_successful(self):
        response = self.client.post(self.get_base_url(), data={}, follow=True)
        self.assertRedirects(response, reverse('inventory:member_items'))
        msg = "{item} has been marked as stored at the Knights".format(item=self.ownership.content_object)
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)

    def test_post_invalid_form(self):
        # Get an item that causes the form to fail. This form should automatically forward when failing
        # as the user can not adjust form data to fix it
        response = self.client.post(self.get_base_url(ownership_id=1), data={}, follow=True)
        self.assertRedirects(response, reverse('inventory:member_items'))
        self.assertHasMessage(response, level=messages.ERROR)


class TestMemberOwnershipAlterView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    base_user_id = 2

    def setUp(self):
        self.ownership = Ownership.objects.get(id=2)
        super(TestMemberOwnershipAlterView, self).setUp()

    def get_base_url(self, ownership_id=None):
        ownership_id = ownership_id or self.ownership.id
        return reverse('inventory:owner_link_edit', kwargs={'ownership_id':ownership_id,})

    def test_class(self):
        self.assertTrue(issubclass(MemberItemLoanFormView, FormView))
        self.assertEqual(MemberOwnershipAlterView.form_class, OwnershipNoteForm)
        self.assertEqual(MemberOwnershipAlterView.template_name, "inventory/membership_adjust_note.html")

    def test_get_successful(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_post_successful(self):
        response = self.client.post(self.get_base_url(), data={}, follow=True)
        self.assertRedirects(response, reverse('inventory:member_items'))
        msg = "Your version of {item} has been updated".format(item=self.ownership.content_object)
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)


