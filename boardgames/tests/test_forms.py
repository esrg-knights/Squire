from django.test import TestCase

from utils.testing.form_test_util import FormValidityMixin

from boardgames.forms import BoardgameFilterForm
from boardgames.models import BoardGame


class BoardgameFilterFormTestCase(FormValidityMixin, TestCase):
    fixtures = ['test_users', 'test_groups', 'test_members.json', 'boardgames/boardgames.json']
    form_class = BoardgameFilterForm

    def test_filter_by_name(self):
        """ Tests name filtering"""
        data = {
            'boardgame_name': 'Mars',
        }
        form = self.assertFormValid(data)
        queryset = form.get_filtered_items(BoardGame.objects.all())
        self.assertEqual(len(queryset),1)
        self.assertIn(data['boardgame_name'], queryset.first().name)

    def test_filter_by_player_count(self):
        # Test general players
        data = {
            'players': 4,
        }
        form = self.assertFormValid(data)
        queryset = form.get_filtered_items(BoardGame.objects.all())
        self.assertEqual(len(queryset), 3)

        # Test min player count
        data = {
            'players': 1,
        }
        form = self.assertFormValid(data)
        queryset = form.get_filtered_items(BoardGame.objects.all())
        self.assertEqual(len(queryset), 1)

        # Test max player count
        data = {
            'players': 5,
        }
        form = self.assertFormValid(data)
        queryset = form.get_filtered_items(BoardGame.objects.all())
        self.assertEqual(len(queryset), 2)

    def test_filter_by_duration(self):
        data = {
            'duration': "L",
        }
        form = self.assertFormValid(data)
        queryset = form.get_filtered_items(BoardGame.objects.all())
        self.assertEqual(len(queryset),2)

    def test_complex_query(self):
        # Results should produce only terraforming mars and gaia project
        data = {
            'boardgame_name': "r",
            'players': 4,
        }
        form = self.assertFormValid(data)
        queryset = form.get_filtered_items(BoardGame.objects.all())
        self.assertEqual(len(queryset),2)
