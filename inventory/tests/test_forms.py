from django import forms
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now
from django.test import TestCase

from utils.testing import FormValidityMixin
from inventory.forms import *
from inventory.models import Ownership, MiscellaneousItem


class TestOwnershipRemovalForm(FormValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    form_class = OwnershipRemovalForm

    def test_cleaning(self):
        self.assertFormValid({}, ownership=Ownership.objects.get(id=1))
        # This one is already taken home
        self.assertFormHasError({}, 'invalid', ownership=Ownership.objects.get(id=2))

    def test_saving(self):
        ownership_obj = Ownership.objects.get(id=1)
        form = self.build_form({}, ownership=ownership_obj)
        self.assertTrue(form.is_valid())
        form.save()
        ownership_obj.refresh_from_db()

        self.assertFalse(ownership_obj.is_active)
        # Note: This check wll fail when tested at midnight
        self.assertEqual(ownership_obj.added_since, now().date())


class TestOwnershipActivationForm(FormValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    form_class = OwnershipActivationForm

    def test_cleaning(self):
        self.assertFormValid({}, ownership=Ownership.objects.get(id=2))
        # This one is already at the Knights
        self.assertFormHasError({}, 'invalid', ownership=Ownership.objects.get(id=1))

    def test_saving(self):
        ownership_obj = Ownership.objects.get(id=2)
        form = self.build_form({}, ownership=ownership_obj)
        self.assertTrue(form.is_valid())
        form.save()
        ownership_obj.refresh_from_db()

        self.assertTrue(ownership_obj.is_active)
        # Note: This check wll fail when tested at midnight
        self.assertEqual(ownership_obj.added_since, now().date())


class TestSimpleModelForms(TestCase):
    def test_OwnershipNoteForm(self):
        self.assertTrue(issubclass(OwnershipNoteForm, forms.ModelForm))
        self.assertEqual(OwnershipNoteForm.Meta.fields, ['note'])

    def test_OwnershipCommitteeForm(self):
        self.assertTrue(issubclass(OwnershipCommitteeForm, forms.ModelForm))
        self.assertEqual(OwnershipCommitteeForm.Meta.fields, ['note', 'added_since'])


class TestAddOwnershipCommitteeLink(FormValidityMixin, TestCase):
    """ Tests AddOwnershipCommitteeLink Form with MiscellaneousItem as the item """
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    form_class = AddOwnershipCommitteeLinkForm

    def get_form_kwargs(self, **kwargs):
        kwargs.setdefault('item', MiscellaneousItem.objects.get(id=3))
        kwargs.setdefault('user', User.objects.get(id=1))
        return super(TestAddOwnershipCommitteeLink, self).get_form_kwargs(**kwargs)

    def test_fields(self):
        self.assertHasField('committee')
        self.assertHasField('note')
        self.assertHasField('is_active')

    def test_committee_queryset_one_group(self):
        """ Tests that a user who belongs only to one group has its choice filled in already"""
        form = self.build_form(None)
        # There are two groups, but user only has 1 group assigned to it
        self.assertEqual(1, form.fields['committee'].queryset.count())
        self.assertEqual(form.fields['committee'].initial, Group.objects.get(id=1).id)
        self.assertTrue(form.fields['committee'].disabled)

    def test_committee_queryset_more_group(self):
        """ Tests that a user belong to more than one group has choices to select the right group """
        form = self.build_form(None, user=User.objects.get(id=100))
        self.assertEqual(2, form.fields['committee'].queryset.count())
        self.assertFalse(form.fields['committee'].disabled)

    def test_committee_allow_all_groups(self):
        """ Tests the correct working of a true value in allow_all_groups """
        form = self.build_form(None, user=User.objects.get(id=100), allow_all_groups=True)
        self.assertEqual(3, form.fields['committee'].queryset.count())


class TestAddOwnershipMemberLink(FormValidityMixin, TestCase):
    """ Tests AddOwnershipCommitteeLink Form with MiscellaneousItem as the item """
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    form_class = AddOwnershipMemberLinkForm

    def get_form_kwargs(self, **kwargs):
        kwargs.setdefault('item', MiscellaneousItem.objects.get(id=3))
        kwargs.setdefault('user', User.objects.get(id=1))
        return super(TestAddOwnershipMemberLink, self).get_form_kwargs(**kwargs)

    def test_fields(self):
        self.assertHasField('member')
        self.assertHasField('note')
        self.assertHasField('is_active')

    def test_member_field_queryset(self):
        form = self.build_form(None)
        # There are three members, but one is deregistered and thus not in the set
        self.assertEqual(2, form.fields['member'].queryset.count())

    def test_cleaning(self):
        form = self.build_form({'member': 2, 'is_active': True})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.instance.member.id, 2)


class TestDeleteOwnershipForm(FormValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    form_class = DeleteOwnershipForm

    def test_form_invalid(self):
        # Assert that links that are active are not deleted
        ownership = Ownership.objects.get(id=1)
        self.assertFormHasError({}, 'is_active', ownership=ownership)

    def test_form_valid(self):
        # Check for a member-owned link
        form = self.assertFormValid({}, ownership=Ownership.objects.get(id=2))
        form.delete_link()
        self.assertFalse(Ownership.objects.filter(id=2).exists())

        # Check for a group-owned link
        form = self.assertFormValid({}, ownership=Ownership.objects.get(id=5))
        form.delete_link()
        self.assertFalse(Ownership.objects.filter(id=5).exists())


class TestFilterCatalogueForm(FormValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    form_class = FilterCatalogueForm

    def get_form_kwargs(self, **kwargs):
        kwargs.setdefault('item_type', ContentType.objects.get_for_model(MiscellaneousItem))
        kwargs.setdefault('include_owner', True)

        return super(TestFilterCatalogueForm, self).get_form_kwargs(**kwargs)

    def test_fields(self):
        self.assertHasField('name')
        self.assertHasField('owner')

    def test_filtering_name(self):
        items = MiscellaneousItem.objects.all()
        # Test searching by name
        form = self.assertFormValid({'name': 'aa'})
        filtered_items =form.get_filtered_items(items)
        self.assertEqual(2, filtered_items.count())
        self.assertTrue(filtered_items.filter(name="Schaar").exists())

        # Test searching by owner (member)
        form = self.assertFormValid({'owner': 'Charlie'})
        filtered_items =form.get_filtered_items(items)
        self.assertEqual(2, filtered_items.count())
        self.assertTrue(filtered_items.filter(name="Flyers").exists())

        # Test searching by owner (group)
        form = self.assertFormValid({'owner': 'ZG'})
        filtered_items =form.get_filtered_items(items)
        self.assertEqual(3, filtered_items.count())

    def test_filtering_with_tussenvoegsels(self):
        items = MiscellaneousItem.objects.all()
        item_type = ContentType.objects.get_for_model(MiscellaneousItem)
        # Test searching by owner (member)
        form = self.assertFormValid({'owner': 'Charlie van der Dommel'}, item_type=item_type)
        filtered_items =form.get_filtered_items(items)
        self.assertEqual(2, filtered_items.count())
        # Test searching by owner (member)
        form = self.assertFormValid({'owner': 'Xena Wolf'}, item_type=item_type)
        filtered_items =form.get_filtered_items(items)
        self.assertEqual(1, filtered_items.count())

    def test_remove_owner_field_query(self):
        form = self.build_form({}, include_owner=False)
        self.assertNotIn('owner', form.fields)

        # Test that owner is ignored if someone tries to hack the system
        form = self.assertFormValid({'owner': 'NOT RELEVANT'}, include_owner=False)
        items = MiscellaneousItem.objects.all()
        filtered_items =form.get_filtered_items(items)
        self.assertEqual(items.count(), filtered_items.count())

class TestFilterOwnershipThroughRelatedItems(FormValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    form_class = FilterOwnershipThroughRelatedItems

    def test_fields(self):
        self.assertHasField('search_field')

    def test_filtering(self):
        ownerships = Ownership.objects.all()

        # Test no filtering
        filtered_ownerships = self.assertFormValid({}).get_filtered_items(ownerships)
        self.assertEqual(6, filtered_ownerships.count())

        # Test Flyers (3 ownership instances)
        filtered_ownerships = self.assertFormValid({'search_field': 'fly'}).get_filtered_items(ownerships)
        self.assertEqual(3, filtered_ownerships.count())

        # Test 'aa' is in 'schaar' and 'Stoel aan de tafel'
        filtered_ownerships = self.assertFormValid({'search_field': 'aa'}).get_filtered_items(ownerships)
        self.assertEqual(3, filtered_ownerships.count())


class TestDeleteItemForm(FormValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    form_class = DeleteItemForm

    def setUp(self):
        self.item = MiscellaneousItem.objects.get(id=1)
        self.ignore_active_links = False

    def get_form_kwargs(self, **kwargs):
        kwargs = super(TestDeleteItemForm, self).get_form_kwargs(**kwargs)
        kwargs.setdefault('item', self.item)
        kwargs.setdefault('ignore_active_links', False)
        return kwargs

    def test_form_invalid(self):
        self.item=MiscellaneousItem.objects.get(id=1)
        self.assertFormHasError({}, 'active_ownerships', ignore_active_links=False)
        self.assertFormValid({}, ignore_active_links=True)

    def test_form_valid(self):
        form = self.assertFormValid({}, item=MiscellaneousItem.objects.get(id=4))
        form.delete_item()
        self.assertFalse(MiscellaneousItem.objects.filter(id=4).exists())


