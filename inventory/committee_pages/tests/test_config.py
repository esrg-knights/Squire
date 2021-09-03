from django.contrib.auth.models import Permission
from django.test import TestCase, Client
from django.urls import reverse


from committees.models import AssociationGroup
from inventory.committee_pages.config import InventoryConfig
from inventory.models import MiscellaneousItem


class TestInventoryCommitteeConfig(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership', 'committees/associationgroups']

    def setUp(self):
        self.config = InventoryConfig()

    def test_quicklinks(self):
        group = AssociationGroup.objects.get(id=1)
        group.site_group.permissions.add(Permission.objects.get(codename='maintain_ownerships_for_miscellaneousitem'))

        quicklinks = self.config.get_local_quicklinks(group)
        self.assertIsInstance(quicklinks[0], dict)
        self.assertEqual(quicklinks[0]['name'], 'miscellaneous item catalogue')
        self.assertEqual(quicklinks[0]['url'], reverse('inventory:catalogue', kwargs={'type_id': MiscellaneousItem})
        )
