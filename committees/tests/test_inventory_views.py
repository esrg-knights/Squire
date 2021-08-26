from django.contrib.messages import SUCCESS
from django.test import TestCase, Client
from django.urls import reverse

from inventory.models import Ownership
from utils.testing.view_test_utils import ViewValidityMixin



# class TestGroupItemOverview(ViewValidityMixin, TestCase):
#     fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
#     base_user_id = 100
#
#     def setUp(self):
#         self.group = Group.objects.get(id=2)
#         super(TestGroupItemOverview, self).setUp()
#
#     def get_base_url(self, group_id=None):
#         group_id = group_id or self.group.id
#         return reverse('inventory:committee_items', kwargs={'group_id':group_id,})
#
#     def test_class(self):
#         self.assertTrue(issubclass(GroupItemsOverview, AssociationGroupMixin))
#         self.assertTrue(issubclass(GroupItemsOverview, SearchFormMixin))
#         self.assertTrue(issubclass(GroupItemsOverview, ListView))
#         self.assertEqual(GroupItemsOverview.search_form_class, FilterOwnershipThroughRelatedItems)
#         self.assertEqual(GroupItemsOverview.template_name, "inventory/committee_inventory.html")
#
#     def test_successful_get(self):
#         response = self.client.get(self.get_base_url(), data={})
#         self.assertEqual(response.status_code, 200)
#
#     def test_context_data(self):
#         response  = self.client.get(self.get_base_url(), data={})
#         context = response.context
#
#         # Ensure that ownerships only contain activated instances
#         self.assertIn('ownerships', context.keys())
#         self.assertEqual(2, context['ownerships'].count())
#
#         # Ensure that the right object types are availlable
#         self.assertIn('content_types', context.keys())
#         self.assertIn(ContentType.objects.get_for_model(MiscellaneousItem), context['content_types'])
#
#
# class TestGroupItemLinkUpdateView(ViewValidityMixin, TestCase):
#     fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
#     base_user_id = 100
#
#     def setUp(self):
#         self.group = Group.objects.get(id=2)
#         self.ownership = Ownership.objects.get(id=3)
#         super(TestGroupItemLinkUpdateView, self).setUp()
#
#     def get_base_url(self, group_id=None, ownership_id=None):
#         group_id = group_id or self.group.id
#         ownership_id = ownership_id or self.ownership.id
#         return reverse('inventory:owner_link_edit', kwargs={'group_id':group_id, 'ownership_id': ownership_id})
#
#     def test_class(self):
#         self.assertTrue(issubclass(GroupItemLinkUpdateView, AssociationGroupMixin))
#         self.assertTrue(issubclass(GroupItemLinkUpdateView, OwnershipMixin))
#         self.assertTrue(issubclass(GroupItemLinkUpdateView, UpdateView))
#         self.assertEqual(GroupItemLinkUpdateView.model, Ownership)
#         self.assertEqual(GroupItemLinkUpdateView.template_name, "inventory/committee_link_edit.html")
#         self.assertEqual(GroupItemLinkUpdateView.fields, ['note', 'added_since'])
#
#     def test_successful_get(self):
#         response = self.client.get(self.get_base_url(), data={})
#         self.assertEqual(response.status_code, 200)
#
#     def test_post_successful(self):
#         response = self.client.post(self.get_base_url(), data={'added_since': '2021-07-29'}, follow=True)
#         self.assertRedirects(response, reverse('inventory:committee_items', kwargs={'group_id': self.group.id}))
#         msg = "Link data has been updated".format()
#         self.assertHasMessage(response, level=SUCCESS, text=msg)
