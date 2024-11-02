from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.test import TestCase
from unittest.mock import Mock

from utils.testing.view_test_utils import TestMixinMixin

from membership_file.tests.mixins import TestMixinWithMemberMiddleware

from committees.mixins import AssociationGroupMixin, GroupSettingsMixin, AssociationGroupPermissionRequiredMixin
from committees.models import AssociationGroup
from committees.tests import get_fake_config


class TestAssociationGroupMixin(TestMixinWithMemberMiddleware, TestMixinMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "committees/associationgroups"]
    mixin_class = AssociationGroupMixin
    base_user_id = 100

    def setUp(self):
        self.associationgroup = AssociationGroup.objects.get(id=1)
        super(TestAssociationGroupMixin, self).setUp()

    def get_as_full_view_class(self, **kwargs):
        cls = super(TestAssociationGroupMixin, self).get_as_full_view_class(**kwargs)
        # Set the config instance. Normally done in urls creation as base value
        cls.config = get_fake_config()
        return cls

    def get_base_url_kwargs(self):
        return {"group_id": self.associationgroup}

    def test_get_successful(self):
        self.assertResponseSuccessful(self._build_get_response())

    def test_context_data(self):
        self._build_get_response(save_view=True)
        context = self.view.get_context_data()
        self.assertEqual(context["association_group"], self.associationgroup)
        self.assertTrue(context["config"].__class__.__name__, "FakeConfig")

    def test_get_no_access(self):
        # Nobody is part of group 3, so this should faulter
        self.assertRaises403(url_kwargs={"group_id": AssociationGroup.objects.get(id=3)})


class TestAssociationGroupPermissionRequiredMixin(TestMixinWithMemberMiddleware, TestMixinMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "committees/associationgroups"]
    mixin_class = AssociationGroupPermissionRequiredMixin
    pre_inherit_classes = [AssociationGroupMixin]
    base_user_id = 100

    def setUp(self):
        self.associationgroup = AssociationGroup.objects.get(id=1)
        self.perm = Permission.objects.get(codename="add_associationgroup")
        self.associationgroup.permissions.add(self.perm)
        self.group_permissions_required = "committees.add_associationgroup"
        super(TestAssociationGroupPermissionRequiredMixin, self).setUp()

    def get_as_full_view_class(self, **kwargs):
        cls = super(TestAssociationGroupPermissionRequiredMixin, self).get_as_full_view_class(**kwargs)
        # Set the config instance. Normally done in urls creation as base value
        cls.config = get_fake_config()
        cls.group_permissions_required = self.group_permissions_required
        return cls

    def get_base_url_kwargs(self):
        return {"group_id": self.associationgroup}

    def test_get_successful(self):
        self.assertResponseSuccessful(self._build_get_response())

    def test_multiple_perms(self):
        self.group_permissions_required = ["committees.add_associationgroup", "committees.delete_associationgroup"]
        self.associationgroup.permissions.add(Permission.objects.get(codename="delete_associationgroup"))
        self.assertResponseSuccessful(self._build_get_response())

    def test_get_no_access(self):
        # Remove the permission
        self.associationgroup.permissions.remove(self.perm)
        self.assertRaises403()


class TestGroupSettingsMixin(TestMixinWithMemberMiddleware, TestMixinMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "committees/associationgroups"]
    mixin_class = GroupSettingsMixin
    base_user_id = 100

    def setUp(self):
        self.associationgroup = AssociationGroup.objects.get(id=1)
        self.settings_mock = Mock()
        super(TestGroupSettingsMixin, self).setUp()

    def get_base_url_kwargs(self):
        return {"group_id": self.associationgroup}

    def get_as_full_view_class(self, **kwargs):
        cls = super(TestGroupSettingsMixin, self).get_as_full_view_class(**kwargs)
        # Set the config instance. Normally done in urls creation as base value
        cls.config = get_fake_config()
        cls.settings_option = self.settings_mock
        return cls

    def test_access(self):
        self.settings_mock.check_option_access.return_value = False
        with self.assertRaises(PermissionDenied):
            self._build_get_response()
        self.settings_mock.check_option_access.return_value = True
        self.assertResponseSuccessful(self._build_get_response())
