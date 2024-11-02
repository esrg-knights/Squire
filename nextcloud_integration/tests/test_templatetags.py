from django.test import TestCase
from django.contrib.auth.models import Permission, User

from nextcloud_integration.models import SquireNextCloudFolder
from nextcloud_integration.templatetags.nextcloud_tags import has_edit_access, has_sync_access


class TemplateTagsTestCase(TestCase):
    fixtures = ["test_users", "test_groups", "test_members.json", "nextcloud_integration/nextcloud_fixtures"]

    def test_edit_access_through_permission(self):
        user = User.objects.get(id=2)
        folder = SquireNextCloudFolder.objects.first()

        self.assertEqual(has_edit_access(user, folder), False)

        user.user_permissions.add(
            Permission.objects.get(
                codename="change_squirenextcloudfolder",
            )
        )
        user = User.objects.get(id=2)  # Fetch the user again to refresh the permissions cache
        self.assertEqual(has_edit_access(user, folder), True)

    def test_synch_access(self):
        user = User.objects.get(id=2)
        self.assertEqual(has_sync_access(user), False)

        user.user_permissions.add(
            Permission.objects.get(
                codename="sync_squirenextcloudfile",
            )
        )
        user = User.objects.get(id=2)  # Fetch the user again to refresh the permissions cache
        self.assertEqual(has_sync_access(user), True)
