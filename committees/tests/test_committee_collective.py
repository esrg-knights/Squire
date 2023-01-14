from django.contrib.auth.models import User
from django.test import TestCase, Client
from unittest.mock import patch

from committees.committeecollective import CommitteeBaseConfig, registry
from committees.models import AssociationGroup


class CommitteeConfigTestCase(TestCase):
    fixtures = ['test_users', 'test_members', 'test_groups', 'committees/associationgroups']

    def setUp(self):
        self.client = Client()
        self.client.force_login(User.objects.get(id=100))
        self.request = self.client.get('').wsgi_request

        self.patcher = patch('committees.committeecollective.user_in_association_group')
        self.mock_user_in_a_group = self.patcher.start()
        self.mock_user_in_a_group.return_value = True

        self.config = CommitteeBaseConfig(registry)
        self.association_group = AssociationGroup.objects.get(id=1)

    def tearDown(self):
        self.patcher.stop()

    def test_user_not_in_group(self):
        self.mock_user_in_a_group.return_value = False
        self.assertEqual(self.config.check_access_validity(self.request, self.association_group), False)

    def test_is_default_for_group(self):
        self.assertEqual(self.config.check_access_validity(self.request, self.association_group), True)
        self.config.group_requires_permission = 'auth.change_user'
        self.assertEqual(self.config.check_access_validity(self.request, self.association_group), False)

    def test_check_access_without_permission_requirement(self):
        self.assertEqual(self.config.check_access_validity(self.request, self.association_group), True)

    def test_check_access_permission_requirement_fails(self):
        self.config.group_requires_permission = 'auth.change_user'
        self.assertEqual(self.config.check_access_validity(self.request, self.association_group), False)

    def test_check_access_permission_requirement_success(self):
        self.config.group_requires_permission = 'auth.change_user'
        self.config.enable_access(self.association_group)
        self.assertEqual(self.config.check_access_validity(self.request, self.association_group), True)
