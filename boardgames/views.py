from django.contrib.contenttypes.models import ContentType
from django.views.generic import ListView


from utils.views import SearchFormMixin

from boardgames.forms import BoardgameFilterForm
from boardgames.models import BoardGame


class BoardGameView(SearchFormMixin, ListView):
    template_name = "boardgames/boardgames_overview.html"
    context_object_name = 'boardgames'
    search_form_class = BoardgameFilterForm

    paginate_by = 15

    def get_queryset(self):
        return self.filter_data(BoardGame.objects.get_all_in_possession())

    def get_context_data(self, **kwargs):
        context = super(BoardGameView, self).get_context_data()
        context['content_type'] = ContentType.objects.get_for_model(BoardGame)
        return context
