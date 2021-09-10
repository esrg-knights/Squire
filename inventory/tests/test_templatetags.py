
from django.contrib.auth.models import User, Group
from django.test import TestCase
from django.test.client import RequestFactory
from django.template import Context

from membership_file.models import Member
from inventory.models import MiscellaneousItem, Ownership
from inventory.templatetags.inventory_tags import render_ownership_tags, get_owned_by


class RenderOwnershipTemplatetagTest(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']

    def setUp(self):
        self.request = RequestFactory().get("/")
        self.request.user = User.objects.get(id=100)
        self.request.member = self.request.user.member
        self.context = Context({'request': self.request,})

    def test_self_owned(self):
        item = MiscellaneousItem.objects.get(id=1)

        results = render_ownership_tags(self.context, item)
        self.assertEqual(results['is_owner'], True)
        self.assertEqual(results['is_owned_by_member'], False)
        self.assertEqual(results['is_owned_by_knights'], True)


    def test_association_owned(self):
        item = MiscellaneousItem.objects.get(id=2)
        results = render_ownership_tags(self.context, item)
        self.assertEqual(results['is_owner'], False)
        self.assertEqual(results['is_owned_by_member'], False)
        self.assertEqual(results['is_owned_by_knights'], True)

    def test_loaned(self):
        """ Tests the sistuation for a loaned item, besides the current users loaned item"""
        item = MiscellaneousItem.objects.get(id=2)
        Ownership(
            member_id=3,
            content_object=item,
            is_active=True,
        ).save()

        results = render_ownership_tags(self.context, item)
        self.assertEqual(results['is_owner'], False)
        self.assertEqual(results['is_owned_by_member'], True)
        self.assertEqual(results['is_owned_by_knights'], True)


    def test_notn_owned(self):
        item = MiscellaneousItem.objects.get(id=4)
        results = render_ownership_tags(self.context, item)
        self.assertEqual(results['is_owner'], False)
        self.assertEqual(results['is_owned_by_member'], False)
        self.assertEqual(results['is_owned_by_knights'], False)


class GetOwnedByTemplatetagTest(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']

    def test_group(self):
        item = MiscellaneousItem.objects.get(id=1)
        group = Group.objects.get(id=2)

        self.assertTrue(get_owned_by(item, group))
        group = Group.objects.get(id=1)
        self.assertFalse(get_owned_by(item, group))

    def test_user(self):
        item = MiscellaneousItem.objects.get(id=1)
        member = Member.objects.get(id=1)

        self.assertTrue(get_owned_by(item, member))
        member = Member.objects.get(id=2)
        self.assertFalse(get_owned_by(item, member))

