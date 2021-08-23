from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, UpdateView, ListView

from core.tests.util import suppress_warnings
from membership_file.util import MembershipRequiredMixin
from utils.testing.media_root_override import override_media_folder
from utils.testing.view_test_utils import ViewValidityMixin
from utils.views import SearchFormMixin

from roleplaying.models import RoleplayingSystem, RoleplayingItem
from roleplaying.views import RoleplaySystemView, SystemDetailView, SystemUpdateView


class TestRoleplaySystemView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'test_roleplaying.json']
    base_user_id = 100
    base_url = reverse_lazy("roleplaying:home")

    def test_class(self):
        self.assertTrue(issubclass(RoleplaySystemView, SearchFormMixin))
        self.assertTrue(issubclass(RoleplaySystemView, ListView))
        self.assertEqual(RoleplaySystemView.template_name, "roleplaying/system_overview.html")
        self.assertEqual(RoleplaySystemView.filter_field_name, "name")
        self.assertEqual(RoleplaySystemView.model, RoleplayingSystem)
        self.assertIsNotNone(RoleplaySystemView.paginate_by)

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_successful_get_anonymous_user(self):
        self.client.logout()
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_template_context(self):
        response  = self.client.get(self.get_base_url(), data={})
        context = response.context

        # assure that it only takes active systems in the queryset
        self.assertEqual(context['roleplay_systems'].count(), 2)
        self.assertEqual(context['roleplay_systems'].first().id, 1)


class TestSystemDetailView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'test_roleplaying.json']
    base_user_id = 100

    def setUp(self):
        self.system = RoleplayingSystem.objects.get(id=1)
        super(TestSystemDetailView, self).setUp()

    def get_base_url(self):
        return reverse("roleplaying:system_details", kwargs={'system_id': self.system.id})

    def test_class(self):
        self.assertTrue(issubclass(SystemDetailView, MembershipRequiredMixin))
        self.assertTrue(issubclass(SystemDetailView, DetailView))
        self.assertEqual(SystemDetailView.template_name, "roleplaying/system_details.html")
        self.assertEqual(SystemDetailView.model, RoleplayingSystem)

    def test_member_items_successful(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_template_context(self):
        response  = self.client.get(self.get_base_url(), data={})
        context = response.context

        # assure that it only takes active systems in the queryset
        self.assertEqual(context['item_type'].model_class(), RoleplayingItem)
        self.assertEqual(context['can_maintain_ownership'], False)
        self.assertEqual(set(context['owned_items']), set(self.system.items.get_all_in_possession()))

        item_class_name = "roleplayingitem"
        self.user.user_permissions.add(Permission.objects.get(codename=f'maintain_ownerships_for_{item_class_name}'))
        response  = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.context['can_maintain_ownership'], True)


class TestSystemUpdateView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'test_roleplaying.json']
    base_user_id = 100

    def setUp(self):
        self.system = RoleplayingSystem.objects.get(id=1)
        super(TestSystemUpdateView, self).setUp()
        self.user.user_permissions.add(Permission.objects.get(codename='change_roleplayingsystem'))

    def get_base_url(self, system_id=None):
        system_id = system_id or self.system.id
        return reverse('roleplaying:system_edit', kwargs={
            'system_id':system_id,
        })

    def test_class(self):
        self.assertTrue(issubclass(SystemUpdateView, MembershipRequiredMixin))
        self.assertTrue(issubclass(SystemUpdateView, PermissionRequiredMixin))
        self.assertTrue(issubclass(SystemUpdateView, UpdateView))
        self.assertEqual(SystemUpdateView.template_name, "roleplaying/system_update.html")

    @suppress_warnings
    def test_not_authorised_get(self):
        self.user.user_permissions.remove(Permission.objects.get(codename='change_roleplayingsystem'))
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 403)

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_post_successful(self):
        data = {'name': 'DnD title', 'short_description': 'some description', 'player_count': '6-',}
        response = self.client.post(self.get_base_url(), data=data, follow=True)

        # Test item update
        self.system.refresh_from_db()
        self.assertEqual(self.system.name, data['name'])

        # Test success message
        msg = "{system_name} has been updated".format(system_name=data['name'])
        self.assertHasMessage(response, level=messages.SUCCESS, text=msg)

        # Test redirect
        self.assertRedirects(response, reverse("roleplaying:system_details", kwargs={'system_id': self.system.id,}))


@override_media_folder()
class TestDownloadDigitalItemView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'test_roleplaying.json']
    base_user_id = 100

    @suppress_warnings
    def test_nonexistent_item(self):
        # Tests that a nonexistent item returns 404
        url = reverse("roleplaying:download_roleplay_item", kwargs={'item_id': 99})
        response = self.client.get(url, data={})
        self.assertEqual(response.status_code, 404)

    @suppress_warnings
    def test_nondigital_file(self):
        # Tests that an item without a digital version returns a 404 error
        url = reverse("roleplaying:download_roleplay_item", kwargs={'item_id': 1})
        response = self.client.get(url, data={})
        self.assertEqual(response.status_code, 404)

    def test_digital_file(self):
        item = RoleplayingItem.objects.get(id=2)

        # Tests that an item without a digital version returns a 404 error
        url = reverse("roleplaying:download_roleplay_item", kwargs={'item_id': item.id})
        response = self.client.get(url, data={})
        self.assertEqual(response.status_code, 200)

        # Check content disposition
        content_disposition = response['Content-Disposition']
        self.assertIn("attachment", content_disposition)

        # Make sure that the file name is equal to the in the instance defined filename
        file_name = content_disposition.split("filename=")[1].split()[0]
        self.assertEqual(file_name, f"{item.local_file_name}.txt")
