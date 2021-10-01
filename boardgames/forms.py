from django.forms import CharField, IntegerField, ChoiceField
from django.db.models import Q

from utils.forms import FilterForm

from boardgames.models import BoardGame


class BoardgameFilterForm(FilterForm):
    boardgame_name = CharField(max_length=100, required=False, label='name')
    players = IntegerField(required=False)
    duration = ChoiceField(required=False,
                           choices=[('', ''), *BoardGame.play_duration_options],
                           initial='')

    def get_filtered_items(self, queryset):
        if self.cleaned_data['boardgame_name']:
            queryset = queryset.filter(name__icontains=self.cleaned_data['boardgame_name'])
        if self.cleaned_data['players']:
            # Players is more complex as there are N+ and N- options. Hence we use Q objects
            queryset = queryset.filter(
                Q(player_min__lte=self.cleaned_data['players']) | Q(player_min__isnull=True),
                Q(player_max__gte=self.cleaned_data['players']) | Q(player_max__isnull=True),
                Q(player_min__isnull=False) | Q(player_max__isnull=False),
            )
        if self.cleaned_data['duration']:
            queryset = queryset.filter(play_duration=self.cleaned_data['duration'])

        return queryset.order_by('name')







