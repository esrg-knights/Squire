from django.test import TestCase
from django.urls import reverse

from utils.testing.view_test_utils import ViewValidityMixin

from boardgames.views import *


class TestBoardGameView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'inventory/test_ownership']
    base_user_id = 2

    def get_base_url(self, content_type=None, item_id=None):
        return reverse('inventory:home')

    def test_class(self):
        self.assertTrue(issubclass(BoardGameView, SearchFormMixin))
        self.assertTrue(issubclass(BoardGameView, ListView))
        self.assertEqual(BoardGameView.template_name, "inventory/front_design/boardgames_overview.html")
        self.assertEqual(BoardGameView.filter_field_name, "name")
        self.assertEqual(BoardGameView.context_object_name, 'boardgames')
        self.assertIsNotNone(BoardGameView.paginate_by)

    def test_successful_get(self):
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

    def test_list_results(self):
        # Assert that it uses the same method
        correct_query = BoardGame.objects.get_all_in_possession()
        url = self.get_base_url(item_id=1)
        response  = self.client.get(url, data={})
        context = response.context
        self.assertEqual(context['boardgames'].count(), correct_query.count())

        # Assert that it uses the filter. Exact value does not matter
        url = self.get_base_url(item_id=1)+"?search_field=mars"
        response  = self.client.get(url, data={})
        context = response.context
        self.assertLess(context['boardgames'].count(), correct_query.count())

    def test_template_context(self):
        response  = self.client.get(self.get_base_url(item_id=1), data={})
        context = response.context

        self.assertEqual(context['content_type'], ContentType.objects.get_for_model(BoardGame))
