from django.views.generic import TemplateView, ListView
from django.views.generic.edit import FormView, FormMixin

from inventory.models import BoardGame, Ownership


class BoardgameView(ListView):
    template_name = "inventory/boardgames_overview.html"
    context_object_name = 'boardgames'

    paginate_by = 10

    def get_queryset(self):
        return BoardGame.objects.get_all_in_possession()

