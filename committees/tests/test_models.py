from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase

from committees.models import AssociationGroup, GroupExternalUrl, AssociationGroupMembership


class TestAssociationGroup(TestCase):
    fixtures = ["test_users", "test_groups", "test_members", "committees/associationgroups"]

    def test_instance_functions(self):
        # Test name function
        assoc_group = AssociationGroup.objects.get(id=4)
        self.assertEqual(assoc_group.name, "Inn drinkers")

        # Test name function
        assoc_group = AssociationGroup.objects.get(id=4)
        self.assertEqual(assoc_group.__str__(), "Inn drinkers")

    def test_has_perm_on_model(self):
        """Tests that the has_perm succesfully functions with perms on the model"""
        assoc_group = AssociationGroup.objects.get(id=4)
        perm = Permission.objects.get(codename="add_associationgroup")
        self.assertEqual(assoc_group.has_perm("committees.add_associationgroup"), False)
        assoc_group.permissions.add(perm)
        self.assertEqual(assoc_group.has_perm("committees.add_associationgroup"), True)

    def test_has_perm_on_site_group(self):
        """Tests that the has_perm succesfully functions with perms on the model"""
        assoc_group = AssociationGroup.objects.get(id=1)
        perm = Permission.objects.get(codename="add_associationgroup")
        self.assertEqual(assoc_group.has_perm("committees.add_associationgroup"), False)
        assoc_group.site_group.permissions.add(perm)
        self.assertEqual(assoc_group.has_perm("committees.add_associationgroup"), True)


class TestGroupExternalUrl(TestCase):
    fixtures = ["test_users", "test_groups", "test_members", "committees/associationgroups"]

    def test_valid_creation(self):
        group = AssociationGroup.objects.get(id=1)
        url = GroupExternalUrl(
            association_group=group,
            name="Google",
            url="https://www.google.com/",
        )
        url.save()
        self.assertIsNotNone(url.id)

    def test_string(self):
        group = AssociationGroup.objects.get(id=1)
        url = GroupExternalUrl(
            association_group=group,
            name="Knights site",
            url="https://www.kotkt.nl/",
        )
        self.assertEqual(str(url), "UUPS - Knights site")


class TestAssociationGroupMembership(TestCase):
    fixtures = ["test_users", "test_groups", "test_members", "committees/associationgroups"]

    def test_unique_together(self):
        original = AssociationGroupMembership.objects.create(
            member_id=3,
            group_id=3,
        )
        self.assertNotEqual(original, None)

        # Attempt to create a copy
        with self.assertRaises(Exception):
            original_clone = AssociationGroupMembership.objects.create(member_id=3, group_id=3)

    def test_member_links(self):
        membership = AssociationGroupMembership(
            group_id=3,
        )
        with self.assertRaises(ValidationError) as e:
            membership.clean()
        self.assertEqual(e.exception.code, "required")

        membership = AssociationGroupMembership(
            member_id=3,
            external_person="Ink ogito",
            group_id=3,
        )
        with self.assertRaises(ValidationError) as e:
            membership.clean()
        self.assertEqual(e.exception.code, "fields_conflict")

    def test_member_name(self):
        self.assertEqual(
            AssociationGroupMembership.objects.get(id=1).member_name,
            str(AssociationGroupMembership.objects.get(id=1).member),
        )
        self.assertEqual(
            AssociationGroupMembership.objects.get(id=5).member_name,
            AssociationGroupMembership.objects.get(id=5).external_person,
        )
