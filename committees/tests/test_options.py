from django.contrib.auth.models import Permission, Group
from django.core.exceptions import ImproperlyConfigured
from django.forms import Form
from django.test import TestCase

from unittest.mock import patch, Mock

from committees.views import BaseSettingsUpdateView
from committees.models import AssociationGroup
from committees.options import SettingsOptionBase, SimpleFormSettingsOption


class SettingOptionsTestCase(TestCase):
    def setUp(self):
        self.options = SettingsOptionBase()
        self.options.option_template_name = "committees/test/test_setting_option_layout.html"

        self.association_group = AssociationGroup.objects.create(
            name="test_group",
            type=AssociationGroup.COMMITTEE,
        )

    @patch("committees.options.get_template")
    def test_render(self, mock: Mock):
        return_value = self.options.render(self.association_group)
        self.assertEqual(return_value._extract_mock_name(), "get_template().render()")
        mock.assert_called_with(self.options.option_template_name)
        context = mock.return_value.render.call_args[0][0]
        self.assertIn("association_group", context.keys())
        self.assertEqual(context["association_group"], self.association_group)

    def test_render_empty(self):
        self.options.option_template_name = None
        self.assertEqual(self.options.render(self.association_group), "")

    def test_configure_urls(self):
        with self.assertRaises(NotImplementedError):
            self.options.get_urls(None)

    def test_url_keyword(self):
        def build_url_pattern(*args):
            return None

        self.options.build_url_pattern = build_url_pattern
        self.assertEqual(self.options.get_urls(None).pattern._route, "")
        self.options.url_keyword = "test_pattern"
        self.assertEqual(self.options.get_urls(None).pattern._route, "test_pattern/")

    def test_check_group_access_group_type(self):
        self.assertEqual(self.options.check_option_access(self.association_group), True)
        self.options.group_type_required = AssociationGroup.ORDER
        self.assertEqual(self.options.check_option_access(self.association_group), False)
        self.association_group.type = AssociationGroup.ORDER
        self.assertEqual(self.options.check_option_access(self.association_group), True)

    def test_check_group_access_group_type_multiple(self):
        self.options.group_type_required = [AssociationGroup.ORDER, AssociationGroup.COMMITTEE, AssociationGroup.BOARD]
        self.assertEqual(self.options.check_option_access(self.association_group), True)

    def test_check_group_access_group_permission_configure_error(self):
        self.options.group_requires_permission = "auth.does_not_exist"
        with self.assertRaises(ImproperlyConfigured) as exc:
            self.options.check_option_access(self.association_group)
        self.assertTrue(str(exc.exception).find("configured incorrectly") >= 0)

    def test_check_group_access_group_permission_denied(self):
        self.options.group_requires_permission = "auth.add_user"
        self.assertEqual(self.options.check_option_access(self.association_group), False)

    def test_check_group_access_group_permission_valid_on_association_group(self):
        perm = Permission.objects.get(
            codename="add_user",
            content_type__app_label="auth",
        )
        self.association_group.permissions.add(perm)
        self.options.group_requires_permission = "auth.add_user"
        self.assertEqual(self.options.check_option_access(self.association_group), True)

    def test_check_group_access_group_permission_valid_on_site_group(self):
        self.association_group.site_group = Group.objects.create()
        self.association_group.save()
        perm = Permission.objects.get(
            codename="add_user",
            content_type__app_label="auth",
        )
        self.association_group.site_group.permissions.add(perm)
        self.options.group_requires_permission = "auth.add_user"
        self.assertEqual(self.options.check_option_access(self.association_group), True)


class SimpleFormSettingsOptionTestCase(TestCase):
    def setUp(self):
        self.options = SimpleFormSettingsOption()

        self.association_group = AssociationGroup.objects.create(
            name="test_group",
            type=AssociationGroup.COMMITTEE,
        )

    def test_get_context_data(self):
        context_data = self.options.get_context_data(self.association_group)
        self.assertIn("settings_url", context_data.keys())

    def test_get_view_class(self):
        test_form = Form
        self.options.option_form_class = test_form

        form_view_class = self.options.get_view_class()
        self.assertTrue(issubclass(form_view_class, BaseSettingsUpdateView))
        self.assertEqual(form_view_class.template_name, "committees/committee_pages/group_settings_edit.html")
        self.assertEqual(form_view_class.form_class, test_form)
