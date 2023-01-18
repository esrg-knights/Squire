from django.contrib.auth.models import User, Permission
from django.test import TestCase, Client
from django.urls import reverse

from utils.testing.view_test_utils import TestMixinMixin

from membership_file.tests.mixins import TestMixinWithMemberMiddleware

from committees.committee_pages.views import AssociationGroupMixin
from committees.models import AssociationGroup
from committees.tests import get_fake_registry


class TestAssociationGroupOverviews(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'committees/associationgroups']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(id=100)
        self.client.force_login(self.user)

        # Add the required permission
        self.user.user_permissions.add(Permission.objects.get(codename='view_associationgroup'))

    def test_committee_overview(self):
        base_url = reverse('committees:committees')
        response  = self.client.get(base_url, data={})
        self.assertEqual(response.status_code, 200)

        group_list = response.context['association_groups']
        self.assertEqual(len(group_list.filter(type=AssociationGroup.COMMITTEE)), len(group_list))
        self.assertEqual(len(group_list.filter(is_public=True)), len(group_list))
        self.assertGreater(len(group_list), 0)

    def test_guild_overview(self):
        base_url = reverse('committees:guilds')
        response  = self.client.get(base_url, data={})
        self.assertEqual(response.status_code, 200)

        group_list = response.context['association_groups']
        self.assertEqual(len(group_list.filter(type=AssociationGroup.ORDER)), len(group_list))
        self.assertEqual(len(group_list.filter(is_public=True)), len(group_list))
        self.assertGreater(len(group_list), 0)

    def test_board_overview(self):
        base_url = reverse('committees:boards')
        response  = self.client.get(base_url, data={})
        self.assertEqual(response.status_code, 200)

        group_list = response.context['association_groups']
        self.assertEqual(len(group_list.filter(type=AssociationGroup.BOARD)), len(group_list))
        self.assertEqual(len(group_list.filter(is_public=True)), len(group_list))
        self.assertGreater(len(group_list), 0)
