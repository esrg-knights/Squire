from django.test import TestCase
from django.template import Template

from unittest.mock import patch, Mock

from utils.testing.view_test_utils import TestMixinMixin

from membership_file.tests.mixins import TestMixinWithMemberMiddleware

from committees.models import AssociationGroup
from committees.options import SettingsOptionBase


class SettingOptionsTestCase(TestCase):

    def setUp(self):
        self.options = SettingsOptionBase()
        self.options.option_template_name = "committees/test/test_setting_option_layout.html"

        self.association_group = AssociationGroup.objects.create(
            name="test_group",
            type=AssociationGroup.COMMITTEE,
        )

    @patch('committees.options.get_template')
    def test_render(self,  mock: Mock):
        return_value = self.options.render(self.association_group)
        self.assertEqual(return_value._extract_mock_name(), 'get_template().render()')
        mock.assert_called_with(self.options.option_template_name)
        context = mock.return_value.render.call_args[0][0]
        self.assertIn('association_group', context.keys())
        self.assertEqual(context['association_group'], self.association_group)

    def test_configure_urls(self):
        with self.assertRaises(NotImplementedError):
            self.options.get_urls(None)

    def test_url_keyword(self):
        def build_url_pattern(*args):
            return None
        self.options.build_url_pattern = build_url_pattern
        self.assertEqual(self.options.get_urls(None).pattern._route, '')
        self.options.url_keyword = 'test_pattern'
        self.assertEqual(self.options.get_urls(None).pattern._route, 'test_pattern/')

    def test_check_group_access_group_type(self):
        self.assertEqual(self.options.check_group_access(self.association_group), True)
        self.options.group_type_required = AssociationGroup.ORDER
        self.assertEqual(self.options.check_group_access(self.association_group), False)
        self.association_group.type = AssociationGroup.ORDER
        self.assertEqual(self.options.check_group_access(self.association_group), True)

    def test_check_group_access_group_type_multiple(self):
        self.options.group_type_required = [
            AssociationGroup.ORDER,
            AssociationGroup.COMMITTEE,
            AssociationGroup.BOARD
        ]
        self.assertEqual(self.options.check_group_access(self.association_group), True)
