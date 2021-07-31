import datetime


from django.core.exceptions import ValidationError
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group, User, Permission
from django.http import HttpResponse
from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse
from django.views.generic.base import View

from core.util import suppress_warnings
from membership_file.models import Member
from utils.testing.view_test_utils import ViewValidityMixin, TestMixinMixin

from inventory.forms import *
from inventory.models import Ownership, BoardGame
from inventory.views import *


class TestMemberItemsView(TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(id=2)
        self.client.force_login(self.user)

        self.base_url = reverse('inventory:member_items')
        # self.base_response = self.client.get(self.base_url, data={})

    @suppress_warnings  # Testing 403 raises a warning that 403 was triggered
    def test_member_items_validity(self):
        response = self.client.get(self.base_url, data={})
        self.assertEqual(response.status_code, 200)

        # Test a user taht is not a member
        self.client.force_login(User.objects.get(id=3))
        response = self.client.get(self.base_url, data={})
        self.assertEqual(response.status_code, 403)

    def test_template_context(self):
        response  = self.client.get(self.base_url, data={})
        context = response.context

        self.assertEqual(context['ownerships'].first().id, 1)
        self.assertEqual(context['ownerships_history'].first().id, 2)


class TestOwnershipMixin(TestMixinMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    mixin_class = OwnershipMixin
    base_user_id = 2

    def setUp(self):
        self.ownership = Ownership.objects.get(id=2)
        super(TestOwnershipMixin, self).setUp()

    def get_base_url_kwargs(self):
        return {'ownership_id': self.ownership.id}

    def test_get_successful(self):
        response = self._build_get_response()
        self.assertEqual(response.status_code, 200)

    def test_context_data(self):
        self._build_get_response(save_view=True)
        context = self.view.get_context_data()
        self.assertIn('ownership', context.keys())
        self.assertEqual(context['ownership'], self.ownership)

    def test_get_no_access(self):
        # A new ownership that is not owned by the current user (member_id=1)
        not_my_ownership = Ownership.objects.create(
            member_id=3,
            content_object=BoardGame.objects.last()
        )
        self.assertRaises403(url_kwargs={'ownership_id': not_my_ownership.id})

    def test_get_non_existent(self):
        self.assertRaises404(url_kwargs={'ownership_id': 99})


class TestMemberItemRemovalFormView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    base_user_id = 2

    def setUp(self):
        self.ownership = Ownership.objects.get(id=1)
        super(TestMemberItemRemovalFormView, self).setUp()

    def get_base_url(self, ownership_id=None):
        ownership_id = ownership_id or self.ownership.id
        return reverse('inventory:member_take_home', kwargs={'ownership_id':ownership_id,})

    def test_class(self):
        self.assertTrue(issubclass(MemberItemRemovalFormView, FormView))
        self.assertTrue(issubclass(MemberItemRemovalFormView, OwnershipMixin))
        self.assertTrue(issubclass(MemberItemRemovalFormView, MembershipRequiredMixin))
        self.assertEqual(MemberItemRemovalFormView.form_class, OwnershipRemovalForm)
        self.assertEqual(MemberItemRemovalFormView.template_name, "inventory/membership_take_home.html")

    def test_get_successful(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_post_successful(self):
        response = self.client.post(self.get_base_url(), data={}, follow=True)
        self.assertRedirects(response, reverse('inventory:member_items'))
        msg = "{item} has been marked as taken home".format(item=self.ownership.content_object)
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)

    def test_post_invalid_form(self):
        # Get an item that causes the form to fail. This form should automatically forward when failing
        # as the user can not adjust form data to fix it
        response = self.client.post(self.get_base_url(ownership_id=2), data={}, follow=True)
        self.assertRedirects(response, reverse('inventory:member_items'))
        self.assertHasMessage(response, level=messages.ERROR)


class TestMemberItemLoanFormView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    base_user_id = 2

    def setUp(self):
        self.ownership = Ownership.objects.get(id=2)
        super(TestMemberItemLoanFormView, self).setUp()

    def get_base_url(self, ownership_id=None):
        ownership_id = ownership_id or self.ownership.id
        return reverse('inventory:member_loan_out', kwargs={'ownership_id':ownership_id,})

    def test_class(self):
        self.assertTrue(issubclass(MemberItemLoanFormView, FormView))
        self.assertTrue(issubclass(MemberItemLoanFormView, OwnershipMixin))
        self.assertTrue(issubclass(MemberItemLoanFormView, MembershipRequiredMixin))
        self.assertEqual(MemberItemLoanFormView.form_class, OwnershipActivationForm)
        self.assertEqual(MemberItemLoanFormView.template_name, "inventory/membership_loan_out.html")

    def test_get_successful(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_post_successful(self):
        response = self.client.post(self.get_base_url(), data={}, follow=True)
        self.assertRedirects(response, reverse('inventory:member_items'))
        msg = "{item} has been marked as stored at the Knights".format(item=self.ownership.content_object)
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)

    def test_post_invalid_form(self):
        # Get an item that causes the form to fail. This form should automatically forward when failing
        # as the user can not adjust form data to fix it
        response = self.client.post(self.get_base_url(ownership_id=1), data={}, follow=True)
        self.assertRedirects(response, reverse('inventory:member_items'))
        self.assertHasMessage(response, level=messages.ERROR)


class TestMemberOwnershipAlterView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    base_user_id = 2

    def setUp(self):
        self.ownership = Ownership.objects.get(id=2)
        super(TestMemberOwnershipAlterView, self).setUp()

    def get_base_url(self, ownership_id=None):
        ownership_id = ownership_id or self.ownership.id
        return reverse('inventory:owner_link_edit', kwargs={'ownership_id':ownership_id,})

    def test_class(self):
        self.assertTrue(issubclass(MemberItemLoanFormView, FormView))
        self.assertEqual(MemberOwnershipAlterView.form_class, OwnershipNoteForm)
        self.assertEqual(MemberOwnershipAlterView.template_name, "inventory/membership_adjust_note.html")

    def test_get_successful(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_post_successful(self):
        response = self.client.post(self.get_base_url(), data={}, follow=True)
        self.assertRedirects(response, reverse('inventory:member_items'))
        msg = "Your version of {item} has been updated".format(item=self.ownership.content_object)
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)


#######################################################


class TestGroupItemOverview(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    base_user_id = 2

    def setUp(self):
        self.group = Group.objects.get(id=2)
        super(TestGroupItemOverview, self).setUp()

    def get_base_url(self, group_id=None):
        group_id = group_id or self.group.id
        return reverse('inventory:committee_items', kwargs={'group_id':group_id,})

    def test_class(self):
        self.assertTrue(issubclass(GroupItemsOverview, GroupMixin))
        self.assertTrue(issubclass(GroupItemsOverview, SearchFormMixin))
        self.assertTrue(issubclass(GroupItemsOverview, ListView))
        self.assertEqual(GroupItemsOverview.search_form_class, FilterOwnershipThroughRelatedItems)
        self.assertEqual(GroupItemsOverview.template_name, "inventory/committee_inventory.html")

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_context_data(self):
        response  = self.client.get(self.get_base_url(), data={})
        context = response.context

        # Ensure that ownerships only contain activated instances
        self.assertIn('ownerships', context.keys())
        self.assertEqual(2, context['ownerships'].count())

        # Ensure that the right object types are availlable
        self.assertIn('content_types', context.keys())
        self.assertIn(ContentType.objects.get_for_model(BoardGame), context['content_types'])


class TestGroupItemLinkUpdateView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    base_user_id = 2

    def setUp(self):
        self.group = Group.objects.get(id=2)
        self.ownership = Ownership.objects.get(id=3)
        super(TestGroupItemLinkUpdateView, self).setUp()

    def get_base_url(self, group_id=None, ownership_id=None):
        group_id = group_id or self.group.id
        ownership_id = ownership_id or self.ownership.id
        return reverse('inventory:owner_link_edit', kwargs={'group_id':group_id, 'ownership_id': ownership_id})

    def test_class(self):
        self.assertTrue(issubclass(GroupItemLinkUpdateView, GroupMixin))
        self.assertTrue(issubclass(GroupItemLinkUpdateView, OwnershipMixin))
        self.assertTrue(issubclass(GroupItemLinkUpdateView, UpdateView))
        self.assertEqual(GroupItemLinkUpdateView.model, Ownership)
        self.assertEqual(GroupItemLinkUpdateView.template_name, "inventory/committee_link_edit.html")
        self.assertEqual(GroupItemLinkUpdateView.fields, ['note', 'added_since'])

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_post_successful(self):
        response = self.client.post(self.get_base_url(), data={'added_since': '2021-07-29'}, follow=True)
        self.assertRedirects(response, reverse('inventory:committee_items', kwargs={'group_id': self.group.id}))
        msg = "Link data has been updated".format()
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)


######################################################


class TestCatalogueMixin(TestMixinMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    mixin_class = CatalogueMixin

    def setUp(self):
        self.content_type = ContentType.objects.get_for_model(BoardGame)
        super(TestCatalogueMixin, self).setUp()

    def get_base_url_kwargs(self):
        return {'type_id': self.content_type.id}

    def test_get_successful(self):
        response = self._build_get_response()
        self.assertEqual(response.status_code, 200)

    def test_get_non_existent(self):
        self.assertRaises404(url_kwargs={
            'type_id': 99,
        })

    def test_context_data(self):
        self._build_get_response(save_view=True)
        context = self.view.get_context_data()
        self.assertIn('item_type', context.keys())
        self.assertEqual(context['item_type'], self.content_type)


class TestItemMixin(TestMixinMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    mixin_class = ItemMixin
    pre_inherit_classes = [CatalogueMixin]

    def setUp(self):
        self.content_type = ContentType.objects.get_for_model(BoardGame)
        self.item = BoardGame.objects.get(id=4)
        super(TestItemMixin, self).setUp()

    def get_base_url_kwargs(self):
        return {
            'type_id': self.content_type.id,
            'item_id': self.item.id,
        }

    def test_get_successful(self):
        response = self._build_get_response()
        self.assertEqual(response.status_code, 200)

    def test_get_non_existent(self):
        self.assertRaises404(url_kwargs={
            'type_id':self.content_type.id,
            'item_id': 99,
        })

    def test_context_data(self):
        self._build_get_response(save_view=True)
        context = self.view.get_context_data()
        self.assertIn('item_type', context.keys())
        self.assertEqual(context['item_type'], self.content_type)


class TestTypeCatalogue(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    base_user_id = 2

    def setUp(self):
        self.content_type = ContentType.objects.get_for_model(BoardGame)
        super(TestTypeCatalogue, self).setUp()

    def get_base_url(self, content_type=None):
        content_type = content_type or self.content_type.id
        return reverse('inventory:catalogue', kwargs={'type_id':content_type,})

    def test_class(self):
        self.assertTrue(issubclass(TypeCatalogue, MembershipRequiredMixin))
        self.assertTrue(issubclass(TypeCatalogue, CatalogueMixin))
        self.assertTrue(issubclass(TypeCatalogue, SearchFormMixin))
        self.assertTrue(issubclass(TypeCatalogue, ListView))
        self.assertEqual(TypeCatalogue.template_name, "inventory/catalogue_for_type.html")

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_context_data(self):
        response  = self.client.get(self.get_base_url(), data={})
        context = response.context

        # Ensure that ownerships only contain activated instances
        self.assertIn('can_add_to_group', context.keys())

        # Ensure that the right object types are availlable
        self.assertIn('can_add_to_member', context.keys())
        self.assertFalse(context['can_add_to_member'])

        # Test that the actual permissions are updated in the context
        self.user.user_permissions.add(Permission.objects.get(codename='can_add_boardgame_for_group'))
        context = self.client.get(self.get_base_url(), data={}).context
        self.assertTrue(context['can_add_to_group'])
        self.assertFalse(context['can_add_to_member'])

        self.user.user_permissions.add(Permission.objects.get(codename='can_add_boardgame_for_member'))
        context = self.client.get(self.get_base_url(), data={}).context
        self.assertTrue(context['can_add_to_group'])
        self.assertTrue(context['can_add_to_member'])


class TestAddLinkCommitteeView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    base_user_id = 2

    def setUp(self):
        self.content_type = ContentType.objects.get_for_model(BoardGame)
        self.item = BoardGame.objects.get(id=4)
        super(TestAddLinkCommitteeView, self).setUp()
        self.user.user_permissions.add(Permission.objects.get(codename='can_add_boardgame_for_group'))

    def get_base_url(self, content_type=None, item_id=None):
        content_type = content_type or self.content_type.id
        item_id = item_id or self.item.id
        return reverse('inventory:catalogue_add_group_link', kwargs={
            'type_id':content_type,
            'item_id': item_id,
        })

    def test_class(self):
        self.assertTrue(issubclass(AddLinkCommitteeView, MembershipRequiredMixin))
        self.assertTrue(issubclass(AddLinkCommitteeView, CatalogueMixin))
        self.assertTrue(issubclass(AddLinkCommitteeView, ItemMixin))
        self.assertTrue(issubclass(AddLinkCommitteeView, PermissionRequiredMixin))
        self.assertTrue(issubclass(AddLinkCommitteeView, CreateView))
        self.assertEqual(AddLinkCommitteeView.template_name, "inventory/catalogue_add_link.html")
        self.assertEqual(AddLinkCommitteeView.form_class, AddOwnershipCommitteeLinkForm)

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    @suppress_warnings
    def test_not_authorised_get(self):
        self.user.user_permissions.remove(Permission.objects.get(codename='can_add_boardgame_for_group'))
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 403)

    def test_post_successful(self):
        group_id = 2
        response = self.client.post(self.get_base_url(), data={'committee': group_id}, follow=True)
        self.assertRedirects(response, reverse('inventory:committee_items', kwargs={'group_id': group_id}))
        msg = "{item} has been placed in {owner}'s inventory".format(
            item = self.item,
            owner=Group.objects.get(id=group_id),
        )
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)


class TestAddLinkMemberView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    base_user_id = 2

    def setUp(self):
        self.content_type = ContentType.objects.get_for_model(BoardGame)
        self.item = BoardGame.objects.get(id=4)
        super(TestAddLinkMemberView, self).setUp()
        self.user.user_permissions.add(Permission.objects.get(codename='can_add_boardgame_for_member'))

    def get_base_url(self, content_type=None, item_id=None):
        content_type = content_type or self.content_type.id
        item_id = item_id or self.item.id
        return reverse('inventory:catalogue_add_member_link', kwargs={
            'type_id':content_type,
            'item_id': item_id,
        })

    def test_class(self):
        self.assertTrue(issubclass(AddLinkMemberView, MembershipRequiredMixin))
        self.assertTrue(issubclass(AddLinkMemberView, CatalogueMixin))
        self.assertTrue(issubclass(AddLinkMemberView, ItemMixin))
        self.assertTrue(issubclass(AddLinkMemberView, PermissionRequiredMixin))
        self.assertTrue(issubclass(AddLinkMemberView, FormView))
        self.assertEqual(AddLinkMemberView.template_name, "inventory/catalogue_add_link.html")
        self.assertEqual(AddLinkMemberView.form_class, AddOwnershipMemberLinkForm)

    @suppress_warnings
    def test_not_authorised_get(self):
        self.user.user_permissions.remove(Permission.objects.get(codename='can_add_boardgame_for_member'))
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 403)

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_post_successful(self):
        member_id = 2
        response = self.client.post(self.get_base_url(), data={'member': member_id}, follow=True)
        self.assertRedirects(response, reverse('inventory:catalogue', kwargs={'type_id': self.content_type.id}))
        msg = "{item} has been placed in {owner}'s inventory".format(
            item = self.item,
            owner=Member.objects.get(id=member_id),
        )
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)
