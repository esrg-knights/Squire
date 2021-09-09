from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType

from inventory.models import Item



class BoardGame(Item):
    """ Defines boardgames """
    bgg_id = models.IntegerField(blank=True, null=True)

    player_min = models.PositiveIntegerField(blank=True, null=True)
    player_max = models.PositiveIntegerField(blank=True, null=True)

    play_duration_options = [
        ('XS', '<15 min.'),
        ('S', '< 1 hour'),
        ('N', '1-2 hours'),
        ('L', '3-4 hours'),
        ('XL', '4+ hours'),
    ]

    play_duration = models.CharField(max_length=2, choices=play_duration_options, blank=True, null=True)

    def get_players_display(self):
        if self.player_min and not self.player_max:
            return f'{self.player_min}+'
        if self.player_min and self.player_max:
            if self.player_min == self.player_max:
                return str(self.player_min)
            else:
                return f'{self.player_min} - {self.player_max}'
        if not self.player_min and self.player_max:
            return f'{self.player_max}-'
        return ''

    def clean(self):
        if self.player_min and self.player_max:
            if self.player_min > self.player_max:
                raise ValidationError("The minimum player count can not be higher than the maximum player count", code='incorrect_value')
