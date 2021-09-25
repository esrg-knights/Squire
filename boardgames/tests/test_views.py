from django.test import TestCase
from django.urls import reverse

from utils.testing.view_test_utils import ViewValidityMixin

from boardgames.forms import BoardgameFilterForm
from boardgames.views import *


class TestBoardGameView(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'boardgames/boardgames.json']
    base_user_id = 2

    def get_base_url(self, content_type=None, item_id=None):
        return reverse('boardgames:home')

    def test_class(self):
        self.assertTrue(issubclass(BoardGameView, SearchFormMixin))
        self.assertTrue(issubclass(BoardGameView, ListView))
        self.assertEqual(BoardGameView.template_name, "boardgames/boardgames_overview.html")
        self.assertEqual(BoardGameView.search_form_class, BoardgameFilterForm)
        self.assertEqual(BoardGameView.context_object_name, 'boardgames')
        self.assertIsNotNone(BoardGameView.paginate_by)

    def test_successful_get_anonymous_user(self):
        self.client.logout()
        response = self.client.get(self.get_base_url(), data={})
        self.assertEqual(response.status_code, 200)

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

    def test_template_context(self):
        response  = self.client.get(self.get_base_url(item_id=1), data={})
        context = response.context

        self.assertEqual(context['content_type'], ContentType.objects.get_for_model(BoardGame))
