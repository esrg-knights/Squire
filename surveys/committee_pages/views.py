from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.views.generic import ListView, FormView, TemplateView
from django.shortcuts import get_object_or_404

from committees.committeecollective import AssociationGroupMixin

from surveys.models import Survey, Response, Question, Answer



class SurveyListView(AssociationGroupMixin, ListView):
    template_name = "surveys/committee_pages/committee_surveys.html"
    context_object_name = 'surveys'

    def get_queryset(self):
        return Survey.objects.filter(
            organisers=self.association_group
        )


class SurveyResultView(AssociationGroupMixin, TemplateView):
    template_name = "surveys/committee_pages/committee_survey_results.html"

    def setup(self, request, *args, **kwargs):
        super(SurveyResultView, self).setup(request, *args, **kwargs)
        self.survey = get_object_or_404(Survey, id=kwargs['survey_id'])
        if self.association_group not in self.survey.organisers.all():
            raise PermissionDenied(f"{self.association_group} has no access to {self.survey}")

    def get_context_data(self, **kwargs):
        return super(SurveyResultView, self).get_context_data(survey=self.survey, **kwargs)




