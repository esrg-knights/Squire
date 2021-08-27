from django.contrib.auth.models import User, Permission, AnonymousUser
from django.test import TestCase

from committees.backends import AssociationGroupAuthBackend
from committees.models import AssociationGroup


class TestAssociationGroupBackend(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members', 'committees/associationgroups']

    def prep_group(self):
        """ Preps user 100 and group 1 for perm check """
        user = User.objects.get(id=100)
        user.groups.clear()

        assoc_group = AssociationGroup.objects.get(id=1)
        perm = Permission.objects.get(codename='add_associationgroup')
        assoc_group.site_group.permissions.add(perm)

        return user, assoc_group

    def test_has_perm(self):
        """ Tests that permission checking also go through associationgroups """
        user, assoc_group = self.prep_group()

        user_has_perm = AssociationGroupAuthBackend().has_perm(
            user, 'committees.add_associationgroup'
        )
        self.assertTrue(user_has_perm)

    def test_has_perm_anonymous_user(self):
        user_has_perm = AssociationGroupAuthBackend().has_perm(
            AnonymousUser(),
            'committees.add_associationgroup'
        )
        self.assertFalse(user_has_perm)

    def test_inactive_user(self):
        """ Tests that inactive users don't validate on a permission check """
        user, assoc_group = self.prep_group()
        user.is_active = False
        user.save()

        user_has_perm = AssociationGroupAuthBackend().has_perm(
            user, 'committees.add_associationgroup'
        )
        self.assertFalse(user_has_perm)

    def test_authentication(self):
        # This backend does not support authentication so should return None
        AssociationGroupAuthBackend().authenticate(
            None,
            username=None,
            password=None,
        )
