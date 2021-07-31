from django import forms
from django.contrib.auth.models import Group, User
from django.utils.timezone import now
from django.test import TestCase

from utils.testing import FormValidityMixin
from inventory.forms import *
from inventory.models import Ownership, BoardGame


class TestOwnershipRemovalForm(FormValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    form_class = OwnershipRemovalForm

    def test_cleaning(self):
        self.assertFormValid({}, ownership=Ownership.objects.get(id=1))
        # This one is already taken home
        self.assertFormHasError({}, 'invalid', ownership=Ownership.objects.get(id=2))

    # @patch('django.utils.timezone.now', side_effect=timezone.datetime(2020, 3, 20, 0, 0)))
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

    # @patch('django.utils.timezone.now', side_effect=timezone.datetime(2020, 3, 20, 0, 0)))
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
    """ Tests AddOwnershipCommitteeLink Form with boardgame as the item """
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    form_class = AddOwnershipCommitteeLinkForm

    def get_form_kwargs(self, **kwargs):
        kwargs.setdefault('item', BoardGame.objects.get(id=3))
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
        form = self.build_form(None, user=User.objects.get(id=2))
        self.assertEqual(2, form.fields['committee'].queryset.count())
        self.assertFalse(form.fields['committee'].disabled)


class TestAddOwnershipMemberLink(FormValidityMixin, TestCase):
    """ Tests AddOwnershipCommitteeLink Form with boardgame as the item """
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    form_class = AddOwnershipMemberLinkForm

    def get_form_kwargs(self, **kwargs):
        kwargs.setdefault('item', BoardGame.objects.get(id=3))
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


class TestFilterOwnershipThroughRelatedItems(FormValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    form_class = FilterOwnershipThroughRelatedItems

    def test_fields(self):
        self.assertHasField('search_field')

    def test_filtering(self):
        ownerships = Ownership.objects.all()

        # Test no filtering
        filtered_ownerships = self.assertFormValid({}).get_filtered_items(ownerships)
        self.assertEqual(5, filtered_ownerships.count())

        # Test terraforming mars (3 ownership instances)
        filtered_ownerships = self.assertFormValid({'search_field': 'mars'}).get_filtered_items(ownerships)
        self.assertEqual(3, filtered_ownerships.count())

        # Test 'ai' is in 'Gaia Project' and 'Pak speelkaarten (ai)'
        filtered_ownerships = self.assertFormValid({'search_field': 'ai'}).get_filtered_items(ownerships)
        self.assertEqual(2, filtered_ownerships.count())

class TestDeleteItemForm(FormValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    form_class = DeleteItemForm

    def setUp(self):
        self.item = BoardGame.objects.get(id=1)
        self.ignore_active_links = False

    def get_form_kwargs(self, **kwargs):
        kwargs = super(TestDeleteItemForm, self).get_form_kwargs(**kwargs)
        kwargs.setdefault('item', self.item)
        kwargs.setdefault('ignore_active_links', False)
        return kwargs

    def test_form_invalid(self):
        self.item=BoardGame.objects.get(id=1)
        self.assertFormHasError({}, 'active_ownerships', ignore_active_links=False)
        self.assertFormValid({}, ignore_active_links=True)

    def test_form_valid(self):
        form = self.assertFormValid({}, item=BoardGame.objects.get(id=4))
        form.delete_item()
        self.assertFalse(BoardGame.objects.filter(id=4).exists())


