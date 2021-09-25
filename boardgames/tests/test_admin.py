from django.test import TestCase
from django.urls import reverse

from utils.testing.view_test_utils import ViewValidityMixin

from boardgames.models import BoardGame
from boardgames.admin import BoardGameAdmin

# Tests for the Admin Panel
class BoardgameAdminTest(ViewValidityMixin, TestCase):
    fixtures = ['test_users.json', 'test_groups', 'test_members.json', 'boardgames/boardgames']
    base_user_id = 1

    # Tests whether we can reach the activity page in the admin panel
    def test_list_page(self):
        app_label, model_name = 'boardgames', 'boardgame'
        url = reverse(f"admin:{app_label}_{model_name}_changelist")

        self.assertValidGetResponse(url=url)

    def test_add_page_new_object(self):
        app_label, model_name = 'boardgames', 'boardgame'
        url = reverse(f"admin:{app_label}_{model_name}_add", kwargs={})

        self.assertValidGetResponse(url=url)

    def test_add_post_reply(self):
        app_label, model_name = 'boardgames', 'boardgame'
        url = reverse(f"admin:{app_label}_{model_name}_add", kwargs={})

        """ Tests the overwritten is_valid in BaseGenericTweakedInlineFormSet """
        post_data = {
            # General inline admin data (required for django formsets to work)
            'inventory-ownership-content_type-object_id-TOTAL_FORMS': ['1'],
            'inventory-ownership-content_type-object_id-INITIAL_FORMS': ['0'],

            # Boardgame data
            'name': ['New one'],

            # Ownership data
            'inventory-ownership-content_type-object_id-0-member': ['1'],
            'inventory-ownership-content_type-object_id-0-added_since': ['2021-08-04'],
            'inventory-ownership-content_type-object_id-0-added_by': ['1'],

            # Redirect option
            '_addanother': True,
        }
        self.assertValidPostResponse(data=post_data, url=url, redirect_url=url)
        self.assertTrue(BoardGame.objects.filter(name='New one').exists())

    def test_admin_current_possession_count_method(self):
        obj = BoardGame.objects.get(id=1)
        self.assertEqual(2, BoardGameAdmin.current_possession_count(obj))
