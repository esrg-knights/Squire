from django.core.exceptions import ValidationError
from django.test import TestCase


from boardgames.models import BoardGame

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

    def test_other_fields(self):
        # This method has no effects in this module, so returns an empty list
        # Its further tested in boardgames
        play_duration_tuple =  BoardGame.play_duration_options[0]

        boardgame = BoardGame(
            name = 'test-game',
            bgg_id = 42,
            play_duration = play_duration_tuple[0],
        )
        other_fields = boardgame.other_fields()

        self.assertEqual(other_fields[0]['name'], 'bgg_id')
        self.assertEqual(other_fields[0]['value'], 42)
        self.assertEqual(other_fields[1]['name'], 'player_min')
        self.assertEqual(other_fields[2]['name'], 'player_max')
        self.assertEqual(other_fields[3]['name'], 'play_duration')
        self.assertEqual(other_fields[3]['verbose_name'], 'play duration')
        self.assertEqual(other_fields[3]['value'], play_duration_tuple[0])
        self.assertEqual(other_fields[3]['display_value'], play_duration_tuple[1])



