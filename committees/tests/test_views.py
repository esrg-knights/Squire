from django.contrib.auth.models import User, Permission
from django.test import TestCase, Client
from django.urls import reverse

from committees.models import AssociationGroup

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
        self.assertEqual(len(group_list.filter(type=AssociationGroup.GUILD)), len(group_list))
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


