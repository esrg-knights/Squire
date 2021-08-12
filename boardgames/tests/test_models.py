from django.core.exceptions import ValidationError
from django.test import TestCase


from inventory.models import BoardGame

class TestBoardGame(TestCase):

    def test_duration_field(self):
        # Test that play_duration is a choice field with 5 choices
        field = BoardGame._meta.get_field("play_duration")
        self.assertIsNotNone(field.choices)
        self.assertEqual(len(field.choices), 5)

    def test_get_players_display(self):
        txt = BoardGame(name='test-game')
        self.assertEqual(txt.get_players_display(), '')

        txt = BoardGame(name='test-game', player_min=2)
        self.assertEqual(txt.get_players_display(), '2+')

        txt = BoardGame(name='test-game', player_max=9)
        self.assertEqual(txt.get_players_display(), '9-')

        txt = BoardGame(name='test-game', player_min=3, player_max=5)
        self.assertEqual(txt.get_players_display(), '3 - 5')

    def test_playter_clean(self):
        try:
            BoardGame(name='test-game', player_min=3, player_max=5).clean()
        except ValidationError as error:
            raise AssertionError("Error raised: "+str(error))

        with self.assertRaises(ValidationError) as error:
            BoardGame(name='test-game', player_min=5, player_max=3).clean()
        self.assertEqual(error.exception.code, 'incorrect_value')
