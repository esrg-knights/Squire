from django.contrib.auth.models import User, AnonymousUser
from django.test import TestCase, Client, RequestFactory
from unittest.mock import patch, Mock

from committees.committeecollective import CommitteeBaseConfig, registry
from committees.options import settings_options_registry, SettingsOptionBase
from committees.models import AssociationGroup


class CommitteeConfigTestCase(TestCase):
    fixtures = ["test_users", "test_members", "test_groups", "committees/associationgroups"]

    def setUp(self):
        self.user = User.objects.get(id=100)
        self.client = Client()
        self.client.force_login(self.user)
        self.request = self.client.get("").wsgi_request

        self.patcher = patch("committees.committeecollective.user_in_association_group")
        self.mock_user_in_a_group = self.patcher.start()
        self.mock_user_in_a_group.return_value = True

        self.config = CommitteeBaseConfig(registry)
        self.association_group = AssociationGroup.objects.get(id=1)

    def tearDown(self):
        self.patcher.stop()

    def test_check_access_super(self):
        # New request with no info WILL fail at the parent
        request = RequestFactory().get(path="")
        request.user = AnonymousUser()
        self.assertEqual(self.config.is_accessible_for(request, self.association_group), False)

    def test_check_access_user_not_in_group(self):
        self.mock_user_in_a_group.return_value = False
        self.assertEqual(self.config.is_accessible_for(self.request, self.association_group), False)

    def test_check_access_no_permissions_set(self):
        self.assertEqual(self.config.is_accessible_for(self.request, self.association_group), True)

    def test_check_access_without_permission_requirement(self):
        self.assertEqual(self.config.is_accessible_for(self.request, self.association_group), True)

    def test_check_access_permission_requirement_fails(self):
        self.config.group_requires_permission = "auth.change_user"
        self.assertEqual(self.config.is_accessible_for(self.request, self.association_group), False)

    def test_check_access_permission_requirement_success(self):
        self.config.group_requires_permission = "auth.change_user"
        self.config.enable_access(self.association_group)
        self.assertEqual(self.config.is_accessible_for(self.request, self.association_group), True)

    def test_enable_access(self):
        perm_name = "auth.change_user"
        self.config.group_requires_permission = perm_name
        self.config.enable_access(self.association_group)
        self.assertEqual(self.user.has_perm(perm_name), True)

    def test_disable_access(self):
        perm_name = "auth.change_user"
        self.config.group_requires_permission = perm_name
        self.config.enable_access(self.association_group)  # Assumes that enable_access works
        self.config.disable_access(self.association_group)
        self.assertEqual(self.user.has_perm(perm_name), False)

    @patch("committees.committeecollective.settings_options_registry")
    def test_setting_option_registry(self, mock_registry: Mock):
        """Test that the option classes defined by the config as registered in the setting options registry"""
        mock_option = Mock()

        class ChildConfig(CommitteeBaseConfig):
            setting_option_classes = [mock_option]
            group_requires_permission = "auth.add_user"

        mock_registry.register.assert_called_with(mock_option)
        self.assertEqual(mock_option.group_requires_permission, "auth.add_user")

    @patch("utils.viewcollectives.ViewCollectiveConfig.get_absolute_url")
    def test_get_absolute_url(self, mock_reverse: Mock):
        self.config.url_name = "test_name"
        self.config.get_absolute_url(self.association_group)
        mock_reverse.assert_called_with(group_id=self.association_group)
