from django.contrib.auth.models import User
from django.test import TestCase
from unittest.mock import patch, Mock

from committees.models import AssociationGroup
from committees.templatetags.association_group_config_tags import *
from committees.templatetags.association_group_tags import *
from committees.committeecollective import CommitteeBaseConfig, registry


class AssociationConfigTagsTestCase(TestCase):
    def setUp(self):
        self.association_group = AssociationGroup.objects.create()

    def test_get_accessible_configs_return_type(self):
        configs = get_accessible_configs(self.association_group)
        self.assertIsInstance(configs, list)
        self.assertIsInstance(configs[0], CommitteeBaseConfig)

    @patch("committees.templatetags.association_group_config_tags.registry")
    def test_get_accessible_configs_filters_inaccessible(self, mock_registry: Mock):
        mock_config = Mock()
        mock_config.check_group_access.return_value = False
        mock_registry.configs.__iter__.return_value = [mock_config]
        configs = get_accessible_configs(self.association_group)

        mock_config.check_group_access.assert_called_with(self.association_group)
        self.assertEqual(configs, [])

    @patch("committees.templatetags.association_group_config_tags.registry")
    def test_get_accessible_configs_filters_accessible(self, mock_registry: Mock):
        mock_config = Mock()
        mock_config.check_group_access.return_value = True
        mock_registry.configs.__iter__.return_value = [mock_config]
        configs = get_accessible_configs(self.association_group)

        mock_config.check_group_access.assert_called_with(self.association_group)
        self.assertEqual(configs, [mock_config])

    def test_get_absolute_url(self):
        mock_config = Mock()
        absolute_url = get_absolute_url(mock_config, self.association_group)
        mock_config.get_absolute_url.assert_called_with(self.association_group)
        self.assertIsNotNone(absolute_url)

    def test_render_options(self):
        mock_setting_option = Mock()
        context = {"association_group": self.association_group}
        render = render_options(context, mock_setting_option)
        mock_setting_option.render.assert_called_with(association_group=self.association_group)
        self.assertIsNotNone(render)


class AssociationGroupTagsTestCase(TestCase):
    @patch("committees.templatetags.association_group_tags.user_in_association_group")
    def test_is_in_group(self, mock_is_in_group: Mock):
        user = User()
        association_group = AssociationGroup()

        mock_is_in_group.return_value = False
        self.assertEqual(is_in_group(user=user, group=association_group), False)
        mock_is_in_group.return_value = True
        self.assertEqual(is_in_group(user=user, group=association_group), True)

    def test_is_type(self):
        association_group = AssociationGroup(type=AssociationGroup.ORDER)
        self.assertTrue(is_type(association_group, "ORDER"))
        self.assertFalse(is_type(association_group, "BOARD"))
        association_group = AssociationGroup(type=AssociationGroup.WORKGROUP)
        self.assertTrue(is_type(association_group, "WORKGROUP"))
        self.assertFalse(is_type(association_group, "CAMPAIGN"))
