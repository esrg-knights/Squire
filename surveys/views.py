from django.contrib.messages import success
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import FormView, ListView

from surveys.forms import SurveyForm
from surveys.models import Survey, Response


class SurveyOverview(ListView):
    template_name = "surveys/survey_overview.html"
    model = Survey
    context_object_name = 'surveys'


class SurveyFormView(FormView):
    template_name = "surveys/survey_form_page.html"
    form_class = SurveyForm
    success_url = reverse_lazy('surveys:overview')

    def get_form_kwargs(self):
        survey = get_object_or_404(Survey, id=self.kwargs['survey_id'])
        response = survey.response_set.filter(member=self.request.member).first()
        if response is None:
            response = Response(survey=survey, member=self.request.member)

        kwargs = super(SurveyFormView, self).get_form_kwargs()
        kwargs.update({
            'survey': survey,
            'response': response
        })
        return kwargs

    def form_valid(self, form):
        success(self.request, "Your answers are succesfully saved",)
        form.save()
        return super(SurveyFormView, self).form_valid(form)

