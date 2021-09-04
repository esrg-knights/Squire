from django.contrib.auth.models import User, AnonymousUser
from django.test import TestCase

from committees.models import AssociationGroup
from committees.utils import user_in_association_group


class TesUserInAssociation(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members', 'committees/associationgroups']

    def test_anonymoususer(self):
        self.assertFalse(user_in_association_group(
            AnonymousUser(),
            AssociationGroup.objects.get(id=3)
        ))

    def test_django_group_connection(self):
        self.assertTrue(user_in_association_group(
            User.objects.get(id=1),
            AssociationGroup.objects.get(id=1)
        ))
        self.assertFalse(user_in_association_group(
            User.objects.get(id=1),
            AssociationGroup.objects.get(id=3)
        ))

    def test_association_group_connection(self):
        self.assertTrue(user_in_association_group(
            User.objects.get(id=100),
            AssociationGroup.objects.get(id=4)
        ))
        self.assertFalse(user_in_association_group(
            User.objects.get(id=100),
            AssociationGroup.objects.get(id=3)
        ))
