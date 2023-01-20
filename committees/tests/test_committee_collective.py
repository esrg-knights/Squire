from django.contrib.auth.models import User, AnonymousUser
from django.test import TestCase, Client, RequestFactory
from unittest.mock import patch

from committees.committeecollective import CommitteeBaseConfig, registry
from committees.models import AssociationGroup


class CommitteeConfigTestCase(TestCase):
    fixtures = ['test_users', 'test_members', 'test_groups', 'committees/associationgroups']

    def setUp(self):
        self.user = User.objects.get(id=100)
        self.client = Client()
        self.client.force_login(self.user)
        self.request = self.client.get('').wsgi_request

        self.patcher = patch('committees.committeecollective.user_in_association_group')
        self.mock_user_in_a_group = self.patcher.start()
        self.mock_user_in_a_group.return_value = True

        self.config = CommitteeBaseConfig(registry)
        self.association_group = AssociationGroup.objects.get(id=1)

    def tearDown(self):
        self.patcher.stop()

    def test_check_access_super(self):
        # New request with no info WILL fail at the parent
        request = RequestFactory().get(path='')
        request.user = AnonymousUser()
        self.assertEqual(self.config.check_access_validity(request, self.association_group), False)

    def test_check_access_user_not_in_group(self):
        self.mock_user_in_a_group.return_value = False
        self.assertEqual(self.config.check_access_validity(self.request, self.association_group), False)

    def test_check_access_no_permissions_set(self):
        self.assertEqual(self.config.check_access_validity(self.request, self.association_group), True)

    def test_check_access_without_permission_requirement(self):
        self.assertEqual(self.config.check_access_validity(self.request, self.association_group), True)

    def test_check_access_permission_requirement_fails(self):
        self.config.group_requires_permission = 'auth.change_user'
        self.assertEqual(self.config.check_access_validity(self.request, self.association_group), False)

    def test_check_access_permission_requirement_success(self):
        self.config.group_requires_permission = 'auth.change_user'
        self.config.enable_access(self.association_group)
        self.assertEqual(self.config.check_access_validity(self.request, self.association_group), True)

    def test_check_inexisting_perm(self):
        with self.assertRaises(KeyError) as error:
            self.config.group_requires_permission = 'xxx.yyy'
            self.config.check_access_validity(self.request, self.association_group)
        self.assertGreater(str(error.exception).find('xxx.yyy'), -1)

    def test_enable_access(self):
        perm_name = 'auth.change_user'
        self.config.group_requires_permission = perm_name
        self.config.enable_access(self.association_group)
        self.assertEqual(self.user.has_perm(perm_name), True)

    def test_disable_access(self):
        perm_name = 'auth.change_user'
        self.config.group_requires_permission = perm_name
        self.config.enable_access(self.association_group)  # Assumes that enable_access works
        self.config.disable_access(self.association_group)
        self.assertEqual(self.user.has_perm(perm_name), False)
