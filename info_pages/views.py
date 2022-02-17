from django.shortcuts import render
from django.views.generic import TemplateView

class InfoPageView(TemplateView):
    template_name = "info_pages/info_pages.html"
    # context_object_name = 'boardgames'
    # search_form_class = BoardgameFilterForm

    # paginate_by = 15

    # def get_queryset(self):
    #     return self.filter_data(BoardGame.objects.get_all_in_possession())

    # def get_context_data(self, **kwargs):
    #     context = super(BoardGameView, self).get_context_data()
    #     context['content_type'] = ContentType.objects.get_for_model(BoardGame)
    #     return context

