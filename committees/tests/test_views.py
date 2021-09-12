from django.contrib.messages import SUCCESS
from django.contrib.auth.models import Group, User, Permission
from django.test import TestCase, Client
from django.urls import reverse
from django.views.generic import TemplateView, FormView

from core.tests.util import suppress_warnings
from utils.testing.view_test_utils import ViewValidityMixin, TestMixinMixin
from utils.views import PostOnlyFormViewMixin

from committees.forms import AssociationGroupMembershipForm, DeleteGroupExternalUrlForm, \
    AddOrUpdateExternalUrlForm, AssociationGroupUpdateForm
from committees.models import AssociationGroup, AssociationGroupMembership, GroupExternalUrl
from committees.views import AssociationGroupMixin, AssociationGroupDetailView, AssociationGroupQuickLinksView, \
    AssociationGroupQuickLinksAddOrUpdateView, AssociationGroupQuickLinksDeleteView,\
    AssociationGroupUpdateView, AssociationGroupMembersView, AssociationGroupMemberUpdateView


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


class TestGroupMixin(TestMixinMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'committees/associationgroups']
    mixin_class = AssociationGroupMixin
    base_user_id = 100

    def setUp(self):
        self.associationgroup = AssociationGroup.objects.get(id=1)
        super(TestGroupMixin, self).setUp()

    def get_base_url_kwargs(self):
        return {'group_id': self.associationgroup.id}

    def test_get_successful(self):
        response = self._build_get_response()
        self.assertEqual(response.status_code, 200)

    def test_context_data(self):
        self._build_get_response(save_view=True)
        context = self.view.get_context_data()
        self.assertEqual(context['association_group'], self.associationgroup)

    def test_get_no_access(self):
        # Nobody is part of group 3, so this should faulter
        self.assertRaises403(url_kwargs={'group_id': 3})

    def test_get_non_existent(self):
        # This group does not exist
        self.assertRaises404(url_kwargs={'group_id': 99})


class TestAssociationGroupDetailView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'committees/associationgroups']
    base_user_id = 100

    def setUp(self):
        self.associationgroup = AssociationGroup.objects.get(id=1)
        super(TestAssociationGroupDetailView, self).setUp()

    def get_base_url(self, associationgroup_id=None):
        associationgroup_id = associationgroup_id or self.associationgroup.id
        return reverse('committees:group_general', kwargs={'group_id':associationgroup_id, })

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupDetailView, AssociationGroupMixin))
        self.assertTrue(issubclass(AssociationGroupDetailView, TemplateView))
        self.assertEqual(AssociationGroupDetailView.template_name, "committees/group_detail_info.html")

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_context_data(self):
        response  = self.client.get(self.get_base_url(), data={})
        context = response.context

        # Ensure that ownerships only contain activated instances
        self.assertEqual(context['tab_overview'], True)
        self.assertIn('quicklinks_internal', context.keys())
        self.assertIsInstance(context['quicklinks_internal'], list)
        self.assertIn('quicklinks_external', context.keys())
        self.assertEqual(set(context['quicklinks_external']), set(self.associationgroup.shortcut_set.all()))


class TestAssociationGroupQuickLinksView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'committees/associationgroups']
    base_user_id = 100

    def setUp(self):
        self.associationgroup = AssociationGroup.objects.get(id=1)
        super(TestAssociationGroupQuickLinksView, self).setUp()

    def get_base_url(self, associationgroup_id=None):
        associationgroup_id = associationgroup_id or self.associationgroup.id
        return reverse('committees:group_quicklinks', kwargs={'group_id':associationgroup_id})

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupQuickLinksView, AssociationGroupMixin))
        self.assertTrue(issubclass(AssociationGroupQuickLinksView, TemplateView))
        self.assertEqual(AssociationGroupQuickLinksView.template_name, "committees/group_detail_quicklinks.html")

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

        self.assertTrue(response.context['tab_overview'])
        self.assertIsInstance(response.context['form'], AddOrUpdateExternalUrlForm)


class TestAssociationGroupQuickLinksAddOrUpdateView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'committees/associationgroups']
    base_user_id = 100

    def setUp(self):
        self.associationgroup = AssociationGroup.objects.get(id=1)
        super(TestAssociationGroupQuickLinksAddOrUpdateView, self).setUp()

    def get_base_url(self, associationgroup_id=None):
        associationgroup_id = associationgroup_id or self.associationgroup.id
        return reverse('committees:group_quicklinks_edit', kwargs={'group_id':associationgroup_id})

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupQuickLinksAddOrUpdateView, AssociationGroupMixin))
        self.assertTrue(issubclass(AssociationGroupQuickLinksAddOrUpdateView, PostOnlyFormViewMixin))
        self.assertTrue(issubclass(AssociationGroupQuickLinksAddOrUpdateView, FormView))
        self.assertEqual(AssociationGroupQuickLinksAddOrUpdateView.form_class, AddOrUpdateExternalUrlForm)

    def test_post_successful_add(self):
        data = {'name': 'Knights site', 'url': 'https://www.kotkt.nl/'}
        response = self.client.post(self.get_base_url(), data=data, follow=True)
        # Test success message
        msg = "{url_name} has been added".format(url_name=data['name'])
        self.assertHasMessage(response, level=SUCCESS, text=msg)

    def test_post_successful_update(self):
        # The id here notes that it is an overwrite action
        data = {'id': 1, 'name': 'Knights site', 'url': 'https://www.kotkt.nl/'}
        response = self.client.post(self.get_base_url(), data=data, follow=True)
        # Test success message
        msg = "{url_name} has been updated".format(url_name=data['name'])
        self.assertHasMessage(response, level=SUCCESS, text=msg)


class TestAssociationGroupQuickLinksDeleteView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'committees/associationgroups']
    base_user_id = 100

    def setUp(self):
        self.associationgroup = AssociationGroup.objects.get(id=1)
        self.quicklink = GroupExternalUrl.objects.get(id=1)
        super(TestAssociationGroupQuickLinksDeleteView, self).setUp()

    def get_base_url(self, associationgroup_id=None, quicklink_id=None):
        associationgroup_id = associationgroup_id or self.associationgroup.id
        quicklink_id = quicklink_id or self.quicklink.id
        return reverse('committees:group_quicklink_delete', kwargs={
            'group_id':associationgroup_id,
            'quicklink_id': quicklink_id,
        })

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupQuickLinksDeleteView, AssociationGroupMixin))
        self.assertTrue(issubclass(AssociationGroupQuickLinksDeleteView, PostOnlyFormViewMixin))
        self.assertTrue(issubclass(AssociationGroupQuickLinksDeleteView, FormView))
        self.assertEqual(AssociationGroupQuickLinksDeleteView.form_class, DeleteGroupExternalUrlForm)
        self.assertEqual(AssociationGroupQuickLinksDeleteView.form_success_method_name, 'delete')

    @suppress_warnings
    def test_nonexisting_link(self):
        data = {}
        response = self.client.post(self.get_base_url(quicklink_id=99), data=data, follow=True)
        self.assertEqual(response.status_code, 404)

    def test_post_successful(self):
        data = {}
        response = self.client.post(self.get_base_url(), data=data, follow=True)
        # Test success message
        msg = "{url_name} has been removed".format(url_name='test_link')
        self.assertHasMessage(response, level=SUCCESS, text=msg)

        # Ensure it's removed
        self.assertFalse(GroupExternalUrl.objects.filter(id=1).exists())

    def test_success_url(self):
        data = {}
        self.assertValidPostResponse(
            data=data,
            redirect_url=reverse('committees:group_quicklinks', kwargs={'group_id': self.associationgroup.id})
        )


class TestAssociationGroupUpdateView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'committees/associationgroups']
    base_user_id = 100

    def setUp(self):
        self.associationgroup = AssociationGroup.objects.get(id=1)
        super(TestAssociationGroupUpdateView, self).setUp()

    def get_base_url(self, associationgroup_id=None):
        associationgroup_id = associationgroup_id or self.associationgroup.id
        return reverse('committees:group_update', kwargs={'group_id':associationgroup_id})

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupUpdateView, AssociationGroupMixin))
        self.assertTrue(issubclass(AssociationGroupUpdateView, FormView))
        self.assertEqual(AssociationGroupUpdateView.template_name, "committees/group_detail_info_edit.html")
        self.assertEqual(AssociationGroupUpdateView.form_class, AssociationGroupUpdateForm)

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

        self.assertTrue(response.context['tab_overview'])

    def test_post_succesful(self):
        data = {'instructions': "new_instructions"}
        self.assertValidPostResponse(
            data=data,
            redirect_url=reverse('committees:group_general', kwargs={'group_id': self.associationgroup.id})
        )
        self.associationgroup.refresh_from_db()
        self.assertEqual(self.associationgroup.instructions.as_raw(), data['instructions'])


class TestAssociationGroupMembersView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'committees/associationgroups']
    base_user_id = 100

    def setUp(self):
        self.associationgroup = AssociationGroup.objects.get(id=1)
        super(TestAssociationGroupMembersView, self).setUp()

    def get_base_url(self, associationgroup_id=None):
        associationgroup_id = associationgroup_id or self.associationgroup.id
        return reverse('committees:group_members', kwargs={'group_id':associationgroup_id})

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupMembersView, AssociationGroupMixin))
        self.assertTrue(issubclass(AssociationGroupMembersView, TemplateView))
        self.assertEqual(AssociationGroupMembersView.template_name, "committees/group_detail_members.html")

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertTrue(context['tab_overview'])
        self.assertIsInstance(context['form'], AssociationGroupMembershipForm)
        self.assertIn('member_links', context.keys())
        self.assertGreater(len(context['member_links']), 0)


class TestAssociationGroupMemberUpdateView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'committees/associationgroups']
    base_user_id = 100

    def setUp(self):
        self.association_group = AssociationGroup.objects.get(id=1)
        super(TestAssociationGroupMemberUpdateView, self).setUp()

    def get_base_url(self, association_group_id=None):
        association_group_id = association_group_id or self.association_group.id
        return reverse('committees:group_members_edit', kwargs={'group_id':association_group_id})

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupMemberUpdateView, AssociationGroupMixin))
        self.assertTrue(issubclass(AssociationGroupMemberUpdateView, PostOnlyFormViewMixin))
        self.assertTrue(issubclass(AssociationGroupMemberUpdateView, FormView))
        self.assertEqual(AssociationGroupMemberUpdateView.form_class, AssociationGroupMembershipForm)

    def test_post_successful(self):
        # The id here notes that it is an overwrite action
        data = {'id': 1}
        response = self.client.post(self.get_base_url(), data=data, follow=True)
        # Test success message
        msg = "{member} has been updated".format(member=self.user.member)
        self.assertHasMessage(response, level=SUCCESS, text=msg)

    def test_success_url(self):
        data = {'id': 3}
        self.assertValidPostResponse(
            data=data,
            redirect_url=reverse("committees:group_members", kwargs={'group_id': self.association_group.id})
        )
