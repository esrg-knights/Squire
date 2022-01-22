from django.test import TestCase
from django.views.generic import ListView, TemplateView

from core.tests.util import suppress_warnings
from committees.tests import AssocationGroupTestingMixin
from utils.testing.view_test_utils import ViewValidityMixin

from surveys.models import Survey
from surveys.committee_pages.views import SurveyResultView, SurveyListView


class TestGroupSurveyOverview(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    fixtures = ['test_users',  'test_groups', 'test_members', 'surveys/test_surveys', 'surveys/test_survey_groups']
    base_user_id = 60
    association_group_id = 61
    url_name = 'surveys:overview'

    def test_class(self):
        self.assertTrue(issubclass(SurveyListView, ListView))
        self.assertEqual(SurveyListView.template_name, "surveys/committee_pages/committee_surveys.html")
        self.assertEqual(SurveyListView.context_object_name, 'surveys')

    def test_successful_get(self):
        response = self.assertValidGetResponse()
        # Test context
        self.assertEqual(response.context['surveys'].count(), 1)
        self.assertIn(Survey.objects.get(id=1), response.context['surveys'])


class TestGroupSurveyDetails(AssocationGroupTestingMixin, ViewValidityMixin, TestCase):
    fixtures = ['test_users',  'test_groups', 'test_members', 'surveys/test_surveys', 'surveys/test_survey_groups']
    base_user_id = 60
    association_group_id = 61
    url_name = 'surveys:results'

    def get_url_kwargs(self, **kwargs):
        kwargs.setdefault('survey_id', 1)
        return super(TestGroupSurveyDetails, self).get_url_kwargs(**kwargs)

    def test_class(self):
        self.assertTrue(issubclass(SurveyResultView, TemplateView))
        self.assertEqual(SurveyResultView.template_name, "surveys/committee_pages/committee_survey_results.html")

    def test_successful_get(self):
        response = self.assertValidGetResponse()
        # Test context
        self.assertEqual(response.context['survey'], Survey.objects.get(id=1))

    @suppress_warnings
    def test_unconnected_survey(self):
        """ Tests that the group can not access surveys the group is not part of """
        self.assertGetResponsePermissionDenied(url=self.get_base_url(survey_id=2))

    @suppress_warnings
    def test_nonexistent_survey(self):
        """ Tests that the group can not access surveys the group is not part of """
        self.assertGetResponseNotFound(url=self.get_base_url(survey_id=33))
