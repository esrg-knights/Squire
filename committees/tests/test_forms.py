from django.test import TestCase

from core.forms import MarkdownForm
from utils.testing import FormValidityMixin
from committees.models import AssociationGroup, AssociationGroupMembership, GroupExternalUrl
from committees.forms import AssociationGroupUpdateForm, AddOrUpdateExternalUrlForm, \
    DeleteGroupExternalUrlForm, AssociationGroupMembershipForm


class TestDeleteGroupExternalUrlForm(FormValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'committees/associationgroups']
    form_class = DeleteGroupExternalUrlForm

    def test_cleaning(self):
        self.assertFormValid({}, instance=GroupExternalUrl.objects.get(id=1))

    def test_deletion(self):
        external_url_obj = GroupExternalUrl.objects.get(id=1)
        form = self.build_form({}, instance=external_url_obj)
        self.assertTrue(form.is_valid())
        form.delete()

        self.assertFalse(GroupExternalUrl.objects.filter(id=1).exists())


class TestAddOrUpdateExternalUrlForm(FormValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'committees/associationgroups']
    form_class = AddOrUpdateExternalUrlForm

    def get_form_kwargs(self, **kwargs):
        kwargs.setdefault('association_group', AssociationGroup.objects.get(id=1))
        return super(TestAddOrUpdateExternalUrlForm, self).get_form_kwargs(**kwargs)

    def test_form_invalid_id(self):
        """ Tests that the id should be part of the known associationgroup """
        self.assertFormHasError({
            'id': 3,
            'name': "new link name",
            'url': "https://www.kotkt.nl/",
        }, code='unconnected')

    def test_creation(self):
        form = self.assertFormValid({
            'name': "new link name",
            'url': "https://www.kotkt.nl/",
        })
        instance, created = form.save()
        self.assertTrue(created)
        self.assertTrue(GroupExternalUrl.objects.filter(id=instance.id).exists())

    def test_update(self):
        new_link_name = "new link name"
        form = self.assertFormValid({
            'id': 1,
            'name': new_link_name,
            'url': "https://www.kotkt.nl/",
        })
        instance, created = form.save()
        self.assertFalse(created)
        self.assertEqual(GroupExternalUrl.objects.get(id=1).name, new_link_name)


class TestAssociationGroupMembershipForm(FormValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'committees/associationgroups']
    form_class = AssociationGroupMembershipForm

    def get_form_kwargs(self, **kwargs):
        kwargs.setdefault('association_group', AssociationGroup.objects.get(id=1))
        return super(TestAssociationGroupMembershipForm, self).get_form_kwargs(**kwargs)

    def test_form_invalid_id(self):
        """ Tests that the id should be part of the known associationgroup """
        self.assertFormHasError({
            'id': 4,
            'role': "Treasurer",
        }, code='unconnected')

    def test_update(self):
        new_role = "Treasurer"
        form = self.assertFormValid({
            'id': 1,
            'role': new_role,
        })
        form.save()
        self.assertEqual(AssociationGroupMembership.objects.get(id=1).role, new_role)


class TestAssociationGroupUpdateForm(TestCase):

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupUpdateForm, MarkdownForm))
        self.assertEqual(AssociationGroupUpdateForm.Meta.model, AssociationGroup)
        self.assertEqual(set(AssociationGroupUpdateForm.Meta.fields), set(['instructions',]))
