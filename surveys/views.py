from django.contrib.messages import success
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.views.generic import FormView, ListView
from django.views.generic.detail import SingleObjectMixin

from surveys.forms import SurveyForm
from surveys.models import Survey, Response


class SurveyOverview(ListView):
    template_name = "surveys/survey_overview.html"
    model = Survey
    context_object_name = 'surveys'


class SurveyFormView(SingleObjectMixin, FormView):
    template_name = "surveys/survey_form_page.html"
    form_class = SurveyForm
    success_url = reverse_lazy('surveys:overview')
    model = Survey
    pk_url_kwarg = 'survey_id'
    context_object_name = 'survey'

    def setup(self, request, *args, **kwargs):
        super(SurveyFormView, self).setup(request, *args, **kwargs)
        self.object = self.get_object()

    def dispatch(self, request, *args, **kwargs):
        if self.object.end_date is not None and self.object.end_date < now():
            return self.render_expired_response()
        if self.object.start_date is not None and self.object.start_date > now():
            raise Http404("This survey does not exist")

        return super(SurveyFormView, self).dispatch(request, *args, **kwargs)

    def render_expired_response(self):
        """ Returns a rendereed template response signalling that the survey has expired """
        expired_template = "surveys/survey_expired.html"

        return TemplateResponse(
            request=self.request,
            template=expired_template,
            context={
                self.context_object_name: self.object,
                'response': Response.objects.filter(
                    member=self.request.member,
                    survey=self.object
                ).prefetch_related(
                    'answer_set'
                ).first()
            }
        )

    def get_form_kwargs(self):
        survey = self.object
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

