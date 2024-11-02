from django.contrib.auth.models import User, Permission
from django.test import TestCase, Client
from django.urls import reverse
from django.views.generic import FormView
from unittest.mock import patch, Mock

from membership_file.tests.mixins import TestMixinWithMemberMiddleware
from utils.testing.view_test_utils import TestMixinMixin

from committees.mixins import GroupSettingsMixin
from committees.models import AssociationGroup
from committees.views import BaseSettingsUpdateView

from . import get_fake_config, get_fake_option


class TestAssociationGroupOverviews(TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "committees/associationgroups"]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(id=100)
        self.client.force_login(self.user)

        # Add the required permission
        self.user.user_permissions.add(Permission.objects.get(codename="view_associationgroup"))

    def test_committee_overview(self):
        base_url = reverse("committees:committees")
        response = self.client.get(base_url, data={})
        self.assertEqual(response.status_code, 200)

        group_list = response.context["association_groups"]
        self.assertEqual(len(group_list.filter(type=AssociationGroup.COMMITTEE)), len(group_list))
        self.assertEqual(len(group_list.filter(is_public=True)), len(group_list))
        self.assertGreater(len(group_list), 0)

    def test_guild_overview(self):
        base_url = reverse("committees:guilds")
        response = self.client.get(base_url, data={})
        self.assertEqual(response.status_code, 200)

        group_list = response.context["association_groups"]
        self.assertEqual(len(group_list.filter(type=AssociationGroup.ORDER)), len(group_list))
        self.assertEqual(len(group_list.filter(is_public=True)), len(group_list))
        self.assertGreater(len(group_list), 0)

    def test_board_overview(self):
        base_url = reverse("committees:boards")
        response = self.client.get(base_url, data={})
        self.assertEqual(response.status_code, 200)

        group_list = response.context["association_groups"]
        self.assertEqual(len(group_list.filter(type=AssociationGroup.BOARD)), len(group_list))
        self.assertEqual(len(group_list.filter(is_public=True)), len(group_list))
        self.assertGreater(len(group_list), 0)


class TestBaseSettingsUpdateView(TestMixinWithMemberMiddleware, TestMixinMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "committees/associationgroups"]
    mixin_class = BaseSettingsUpdateView
    base_user_id = 100

    def setUp(self):
        self.association_group = AssociationGroup.objects.get(id=1)
        super(TestBaseSettingsUpdateView, self).setUp()
        self.response = self._build_get_response(save_view=True)

    def get_as_full_view_class(self, *args, **kwargs):
        view_class = super(TestBaseSettingsUpdateView, self).get_as_full_view_class(*args, **kwargs)
        view_class.config = get_fake_config()
        view_class.settings_option = get_fake_option()
        return view_class

    def get_base_url_kwargs(self):
        kwargs = super(TestBaseSettingsUpdateView, self).get_base_url_kwargs()
        kwargs["group_id"] = self.association_group
        return kwargs

    def get_base_url(self):
        return "/well/some-elaborate-url"

    def test_class(self):
        self.assertTrue(issubclass(BaseSettingsUpdateView, GroupSettingsMixin))
        self.assertTrue(issubclass(BaseSettingsUpdateView, FormView))
        self.assertEqual(BaseSettingsUpdateView.template_name, "committees/committee_pages/group_settings_edit.html")

    def test_successful_get(self):
        self.assertEqual(self.response.status_code, 200)

    def test_form_kwargs(self):
        form_kwargs = self.view.get_form_kwargs()
        self.assertIn("instance", form_kwargs.keys())
        self.assertEqual(form_kwargs["instance"], self.association_group)

    @patch("committees.views.messages")
    def test_form_valid(self, mock_messages: Mock):
        mock_form = Mock()
        self.view.form_valid(mock_form)
        mock_form.save.assert_called()
        mock_messages.success.assert_called()

    def test_get_success_url(self):
        self.assertEqual(self.view.get_success_url(), self.get_base_url())
