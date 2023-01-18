from django.core.exceptions import PermissionDenied
from django.test import TestCase
from unittest.mock import Mock

from utils.testing.view_test_utils import TestMixinMixin

from membership_file.tests.mixins import TestMixinWithMemberMiddleware

from committees.committee_pages.views import AssociationGroupMixin, GroupSettingsMixin
from committees.models import AssociationGroup
from committees.tests import get_fake_registry


class TestAssociationGroupMixin(TestMixinWithMemberMiddleware, TestMixinMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'committees/associationgroups']
    mixin_class = AssociationGroupMixin
    base_user_id = 100

    def setUp(self):
        self.associationgroup = AssociationGroup.objects.get(id=1)
        super(TestAssociationGroupMixin, self).setUp()

    def get_as_full_view_class(self):
        cls = super(TestAssociationGroupMixin, self).get_as_full_view_class()
        # Set the config instance. Normally done in urls creation as base value
        cls.config = get_fake_registry()
        return cls

    def get_base_url_kwargs(self):
        return {'group_id': self.associationgroup}

    def test_get_successful(self):
        response = self._build_get_response()
        self.assertEqual(response.status_code, 200)

    def test_context_data(self):
        self._build_get_response(save_view=True)
        context = self.view.get_context_data()
        self.assertEqual(context['association_group'].COMMITTEE, True)
        self.assertEqual(context['association_group'].ORDER, False)
        self.view.association_group.type = AssociationGroup.ORDER
        context = self.view.get_context_data()
        self.assertEqual(context['association_group'].ORDER, True)
        self.assertEqual(context['association_group'].CAMPAIGN, False)
        self.view.association_group.type = AssociationGroup.CAMPAIGN
        context = self.view.get_context_data()
        self.assertEqual(context['association_group'].CAMPAIGN, True)
        self.assertEqual(context['association_group'].BOARD, False)
        self.view.association_group.type = AssociationGroup.BOARD
        context = self.view.get_context_data()
        self.assertEqual(context['association_group'].BOARD, True)
        self.assertEqual(context['association_group'].COMMITTEE, False)

    def test_get_no_access(self):
        # Nobody is part of group 3, so this should faulter
        self.assertRaises403(url_kwargs={'group_id': AssociationGroup.objects.get(id=3)})


class TestGroupSettingsMixin(TestMixinWithMemberMiddleware, TestMixinMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'committees/associationgroups']
    mixin_class = GroupSettingsMixin
    base_user_id = 100

    def setUp(self):
        self.associationgroup = AssociationGroup.objects.get(id=1)
        self.settings_mock = Mock()
        super(TestGroupSettingsMixin, self).setUp()

    def get_base_url_kwargs(self):
        return {'group_id': self.associationgroup}

    def get_as_full_view_class(self):
        cls = super(TestGroupSettingsMixin, self).get_as_full_view_class()
        # Set the config instance. Normally done in urls creation as base value
        cls.config = get_fake_registry()
        cls.config.settings = self.settings_mock
        return cls

    def test_access(self):
        self.settings_mock.can_access.return_value = False
        with self.assertRaises(PermissionDenied):
            self._build_get_response()
        self.settings_mock.return_value.can_access.return_value = True
        with self.assertRaises(PermissionDenied):
            self._build_get_response()
