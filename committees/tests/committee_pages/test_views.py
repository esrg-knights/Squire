from django.contrib.messages import SUCCESS
from django.test import TestCase
from django.urls import reverse
from django.views.generic import TemplateView, FormView

from core.tests.util import suppress_warnings
from membership_file.tests.mixins import TestMixinWithMemberMiddleware
from utils.testing.view_test_utils import ViewValidityMixin, TestMixinMixin
from utils.views import PostOnlyFormViewMixin

from committees.forms import AssociationGroupMembershipForm, DeleteGroupExternalUrlForm, AddOrUpdateExternalUrlForm
from committees.mixins import AssociationGroupMixin, GroupSettingsMixin
from committees.models import AssociationGroup, GroupExternalUrl
from committees.committee_pages.views import *
from committees.committeecollective import CommitteeBaseConfig, registry
from committees.tests.committee_pages.utils import AssocationGroupTestingMixin


class FakeConfig(CommitteeBaseConfig):
    url_keyword = "main"
    name = "Overview"
    url_name = "group_general"
    order_value = 10


class TestGroupMixin(TestMixinWithMemberMiddleware, TestMixinMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "committees/associationgroups"]
    mixin_class = AssociationGroupMixin
    base_user_id = 100

    def setUp(self):
        self.associationgroup = AssociationGroup.objects.get(id=1)
        super(TestGroupMixin, self).setUp()

    def get_as_full_view_class(self, **kwargs):
        cls = super(TestGroupMixin, self).get_as_full_view_class(**kwargs)
        # Set the config instance. Normally done in urls creation as base value
        cls.config = FakeConfig(registry)
        return cls

    def get_base_url_kwargs(self):
        return {"group_id": self.associationgroup}

    def test_get_successful(self):
        response = self._build_get_response()
        self.assertEqual(response.status_code, 200)

    def test_context_data(self):
        self._build_get_response(save_view=True)
        context = self.view.get_context_data()
        self.assertEqual(context["association_group"], self.associationgroup)


class TestAssociationGroupDetailView(ViewValidityMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "committees/associationgroups"]
    base_user_id = 100

    def setUp(self):
        self.associationgroup = AssociationGroup.objects.get(id=1)
        super(TestAssociationGroupDetailView, self).setUp()

    def get_base_url(self, associationgroup=None):
        associationgroup = associationgroup or self.associationgroup
        return reverse(
            "committees:group_general",
            kwargs={
                "group_id": associationgroup,
            },
        )

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupDetailView, AssociationGroupMixin))
        self.assertTrue(issubclass(AssociationGroupDetailView, TemplateView))
        self.assertEqual(AssociationGroupDetailView.template_name, "committees/committee_pages/group_detail_info.html")

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_context_data(self):
        response = self.client.get(self.get_base_url(), data={})
        context = response.context

        # Ensure that ownerships only contain activated instances
        self.assertIn("quicklinks_internal", context.keys())
        self.assertIsInstance(context["quicklinks_internal"], list)
        self.assertIn("quicklinks_external", context.keys())
        self.assertEqual(set(context["quicklinks_external"]), set(self.associationgroup.shortcut_set.all()))


class TestAssociationSettingsView(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    association_group_type = AssociationGroup.COMMITTEE
    fixtures = ["test_users", "test_groups", "test_members.json", "committees/associationgroups"]
    url_name = "settings:settings_home"
    base_user_id = 100

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupSettingsView, GroupSettingsMixin))
        self.assertTrue(issubclass(AssociationGroupSettingsView, TemplateView))
        self.assertEqual(
            AssociationGroupSettingsView.template_name, "committees/committee_pages/group_settings_home.html"
        )

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)


class TestAssociationGroupQuickLinksView(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    association_group_type = AssociationGroup.COMMITTEE
    fixtures = ["test_users", "test_groups", "test_members.json", "committees/associationgroups"]
    url_name = "settings:group_quicklinks"
    base_user_id = 100

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupQuickLinksView, GroupSettingsMixin))
        self.assertTrue(issubclass(AssociationGroupQuickLinksView, TemplateView))
        self.assertEqual(
            AssociationGroupQuickLinksView.template_name, "committees/committee_pages/group_detail_quicklinks.html"
        )

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

        self.assertIsInstance(response.context["form"], AddOrUpdateExternalUrlForm)


class TestAssociationGroupQuickLinksAddOrUpdateView(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    association_group_id = 1
    fixtures = ["test_users", "test_groups", "test_members.json", "committees/associationgroups"]
    url_name = "settings:group_quicklinks_edit"
    base_user_id = 100

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupQuickLinksAddOrUpdateView, GroupSettingsMixin))
        self.assertTrue(issubclass(AssociationGroupQuickLinksAddOrUpdateView, PostOnlyFormViewMixin))
        self.assertTrue(issubclass(AssociationGroupQuickLinksAddOrUpdateView, FormView))
        self.assertEqual(AssociationGroupQuickLinksAddOrUpdateView.form_class, AddOrUpdateExternalUrlForm)

    def test_post_successful_add(self):
        data = {"name": "Knights site", "url": "https://www.kotkt.nl/"}
        response = self.client.post(self.get_base_url(), data=data, follow=True)
        # Test success message
        msg = "{url_name} has been added".format(url_name=data["name"])
        self.assertHasMessage(response, level=SUCCESS, text=msg)

    def test_post_successful_update(self):
        # The id here notes that it is an overwrite action
        data = {"id": 1, "name": "Knights site", "url": "https://www.kotkt.nl/"}
        response = self.client.post(self.get_base_url(), data=data, follow=True)
        # Test success message
        msg = "{url_name} has been updated".format(url_name=data["name"])
        self.assertHasMessage(response, level=SUCCESS, text=msg)


class TestAssociationGroupQuickLinksDeleteView(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    association_group_id = 1
    fixtures = ["test_users", "test_groups", "test_members.json", "committees/associationgroups"]
    url_name = "settings:group_quicklink_delete"
    base_user_id = 100

    def setUp(self):
        self.quicklink = GroupExternalUrl.objects.get(id=1)
        super(TestAssociationGroupQuickLinksDeleteView, self).setUp()

    def get_url_kwargs(self, **url_kwargs):
        url_kwargs.setdefault("quicklink_id", self.quicklink.id)
        return super(TestAssociationGroupQuickLinksDeleteView, self).get_url_kwargs(**url_kwargs)

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupQuickLinksDeleteView, GroupSettingsMixin))
        self.assertTrue(issubclass(AssociationGroupQuickLinksDeleteView, PostOnlyFormViewMixin))
        self.assertTrue(issubclass(AssociationGroupQuickLinksDeleteView, FormView))
        self.assertEqual(AssociationGroupQuickLinksDeleteView.form_class, DeleteGroupExternalUrlForm)
        self.assertEqual(AssociationGroupQuickLinksDeleteView.form_success_method_name, "delete")

    @suppress_warnings
    def test_nonexisting_link(self):
        data = {}
        response = self.client.post(self.get_base_url(quicklink_id=99), data=data, follow=True)
        self.assertEqual(response.status_code, 404)

    def test_post_successful(self):
        data = {}
        response = self.client.post(self.get_base_url(), data=data, follow=True)
        # Test success message
        msg = "{url_name} has been removed".format(url_name="test_link")
        self.assertHasMessage(response, level=SUCCESS, text=msg)

        # Ensure it's removed
        self.assertFalse(GroupExternalUrl.objects.filter(id=1).exists())

    def test_success_url(self):
        data = {}
        self.assertValidPostResponse(
            data=data,
            redirect_url=reverse("committees:settings:group_quicklinks", kwargs={"group_id": self.association_group}),
        )


class TestAssociationGroupMembersView(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    association_group_id = 1
    fixtures = ["test_users", "test_groups", "test_members.json", "committees/associationgroups"]
    url_name = "settings:group_members"
    base_user_id = 100

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupMembersView, GroupSettingsMixin))
        self.assertTrue(issubclass(AssociationGroupMembersView, TemplateView))
        self.assertEqual(
            AssociationGroupMembersView.template_name, "committees/committee_pages/group_detail_members.html"
        )

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertIsInstance(context["form"], AssociationGroupMembershipForm)
        self.assertIn("member_links", context.keys())
        self.assertGreater(len(context["member_links"]), 0)


class TestAssociationGroupMemberUpdateView(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    association_group_id = 1
    base_user_id = 100
    fixtures = ["test_users", "test_groups", "test_members.json", "committees/associationgroups"]
    url_name = "settings:group_members_edit"

    def test_class(self):
        self.assertTrue(issubclass(AssociationGroupMemberUpdateView, GroupSettingsMixin))
        self.assertTrue(issubclass(AssociationGroupMemberUpdateView, PostOnlyFormViewMixin))
        self.assertTrue(issubclass(AssociationGroupMemberUpdateView, FormView))
        self.assertEqual(AssociationGroupMemberUpdateView.form_class, AssociationGroupMembershipForm)

    def test_post_successful(self):
        # The id here notes that it is an overwrite action
        data = {"id": 1}
        response = self.client.post(self.get_base_url(), data=data, follow=True)
        # Test success message
        msg = "{member} has been updated".format(member=self.user.member)
        self.assertHasMessage(response, level=SUCCESS, text=msg)

    def test_success_url(self):
        data = {"id": 3}
        self.assertValidPostResponse(
            data=data,
            redirect_url=reverse("committees:settings:group_members", kwargs={"group_id": self.association_group}),
        )
