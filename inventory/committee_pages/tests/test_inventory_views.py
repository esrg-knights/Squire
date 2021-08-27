from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group, User, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet
from django.test import TestCase, Client
from django.urls import reverse
from django.views.generic import DetailView, FormView, UpdateView, CreateView, ListView

from committees.views import AssociationGroupMixin
from core.tests.util import suppress_warnings
from membership_file.models import Member
from membership_file.util import MembershipRequiredMixin
from utils.testing.view_test_utils import ViewValidityMixin, TestMixinMixin
from utils.views import SearchFormMixin, RedirectMixin

from inventory.forms import *
from inventory.models import Ownership, MiscellaneousItem
from inventory.views import *
from inventory.views import OwnershipMixin, CatalogueMixin, ItemMixin, OwnershipCatalogueLinkMixin

from inventory.models import Ownership
from inventory.committee_pages.views import AssociationGroupInventoryView, AssociationGroupItemLinkUpdateView


class TestAssociationGroupInventoryView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership', 'committees/associationgroups']
    base_user_id = 100

    def setUp(self):
        self.group = Group.objects.get(id=2)
        super(TestAssociationGroupInventoryView, self).setUp()

    def get_base_url(self, group_id=None):
        group_id = group_id or self.group.id
        return reverse('committees:group_inventory', kwargs={'group_id':group_id,})

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupInventoryView, AssociationGroupMixin))
        self.assertTrue(issubclass(AssociationGroupInventoryView, SearchFormMixin))
        self.assertTrue(issubclass(AssociationGroupInventoryView, ListView))
        self.assertEqual(AssociationGroupInventoryView.search_form_class, FilterOwnershipThroughRelatedItems)
        self.assertEqual(AssociationGroupInventoryView.template_name,
                         "inventory/committee_pages/group_detail_inventory.html")

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_context_data(self):
        response  = self.client.get(self.get_base_url(), data={})
        context = response.context

        # Ensure that ownerships only contain activated instances
        self.assertIn('ownerships', context.keys())
        self.assertEqual(2, context['ownerships'].count())

        # Ensure that the right object types are availlable
        self.assertIn('content_types', context.keys())
        self.assertIn(ContentType.objects.get_for_model(MiscellaneousItem), context['content_types'])


class TestAssociationGroupItemLinkUpdateView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership', 'committees/associationgroups']
    base_user_id = 100

    def setUp(self):
        self.group = Group.objects.get(id=2)
        self.ownership = Ownership.objects.get(id=3)
        super(TestAssociationGroupItemLinkUpdateView, self).setUp()

    def get_base_url(self, group_id=None, ownership_id=None):
        group_id = group_id or self.group.id
        ownership_id = ownership_id or self.ownership.id
        return reverse('committees:group_inventory', kwargs={'group_id':group_id, 'ownership_id': ownership_id})

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupItemLinkUpdateView, AssociationGroupMixin))
        self.assertTrue(issubclass(AssociationGroupItemLinkUpdateView, OwnershipMixin))
        self.assertTrue(issubclass(AssociationGroupItemLinkUpdateView, UpdateView))
        self.assertEqual(AssociationGroupItemLinkUpdateView.model, Ownership)
        self.assertEqual(AssociationGroupItemLinkUpdateView.template_name, "inventory/committee_pages/group_detail_inventory_link_update.html")
        self.assertEqual(AssociationGroupItemLinkUpdateView.fields, ['note', 'added_since'])

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_post_successful(self):
        response = self.client.post(self.get_base_url(), data={'added_since': '2021-07-29'}, follow=True)
        self.assertRedirects(response, reverse('committees:group_inventory', kwargs={'group_id': self.group.id}))
        msg = "Link data has been updated".format()
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)
