from django.urls import path, include, reverse

from committees.committeecollective import CommitteeBaseConfig

from .views import SurveyListView, SurveyResultView


class SurveyConfig(CommitteeBaseConfig):
    url_keyword = 'surveys'
    name = 'Surveys'
    icon_class = 'fas fa-list'
    url_name = 'surveys:overview'
    group_requires_permission = 'surveys.view_survey'
    namespace = "surveys"

    def get_urls(self):
        """ Builds a list of urls """
        return [
            path('', SurveyListView.as_view(config=self), name='overview'),
            path('<int:survey_id>/', SurveyResultView.as_view(config=self), name='results'),
        ]
