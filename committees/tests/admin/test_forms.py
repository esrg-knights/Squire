from django.test import TestCase
from unittest.mock import patch, Mock

from committees.committee_pages.config import AssociationGroupHomeConfig
from utils.testing.form_test_util import FormValidityMixin

from committees.admin.forms import AssociationGroupsTabAccessForm, ConfigTabSelectWidget
from committees.admin.models import AssociationGroupPanelControl


class AssociationGroupsTabAccessFormTestCase(FormValidityMixin, TestCase):
    fixtures = ["test_users", "test_groups", "test_members", "committees/associationgroups"]
    form_class = AssociationGroupsTabAccessForm

    def setUp(self):
        self.association_group = AssociationGroupPanelControl.objects.first()

    def get_form_kwargs(self, instance=None, **kwargs):
        instance = instance or self.association_group
        return super(AssociationGroupsTabAccessFormTestCase, self).get_form_kwargs(instance=instance, **kwargs)

    def test_config_fields(self):
        form = self.build_form(data={})
        config_name = AssociationGroupHomeConfig.name
        self.assertIn(config_name, form.fields.keys())
        self.assertEqual(form.fields[config_name].required, False)
        self.assertEqual(form.fields[config_name].initial, None)
        self.assertIsInstance(form.fields[config_name].widget, ConfigTabSelectWidget)
        self.assertEqual(
            form.fields,
            form.base_fields,
            msg="Form base_fields and fields attribute should be the same for the admin to work",
        )

    @staticmethod
    def _create_mock_committee_config(registry_mock, name, group_access=True, is_default=False):
        config_mock = Mock()
        config_mock.name = name
        config_mock.check_group_access.return_value = group_access
        config_mock.is_default_for_group.return_value = is_default
        registry_mock.configs.__iter__.return_value = [config_mock]
        return config_mock

    @patch("committees.admin.forms.registry")
    def test_form_saving_disable(self, registry_mock: Mock):
        config_mock = self._create_mock_committee_config(registry_mock, "mock_name", group_access=True)

        form = self.assertFormValid(data={})
        form.save()
        config_mock.disable_access.assert_called()

        # Ensure that its not disabled when the state was already correct
        config_mock = self._create_mock_committee_config(registry_mock, "mock_name", group_access=False)

        form = self.assertFormValid(data={})
        form.save()
        config_mock.disable_access.assert_not_called()

    @patch("committees.admin.forms.registry")
    def test_form_saving_enable(self, registry_mock: Mock):
        config_mock = self._create_mock_committee_config(registry_mock, "mock_name", group_access=False)

        form = self.assertFormValid(data={"mock_name": True})
        form.save()
        config_mock.enable_access.assert_called()

        # Ensure that its not disabled when the state was already correct
        config_mock = self._create_mock_committee_config(registry_mock, "mock_name", group_access=True)

        form = self.assertFormValid(data={"mock_name": True})
        form.save()
        config_mock.enable_access.assert_not_called()

    @patch("committees.admin.forms.registry")
    def test_form_saving_defaulted(self, registry_mock: Mock):
        config_mock = self._create_mock_committee_config(registry_mock, "mock_name", is_default=True)

        form = self.assertFormValid(data={"mock_name": True})
        form.save()
        config_mock.enable_access.assert_not_called()
        config_mock.disable_access.assert_not_called()

    def test_save_m2m(self):
        form = self.build_form(data={})
        try:
            form.save_m2m()
        except Exception as e:
            raise AssertionError(e)
