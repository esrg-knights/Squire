import datetime
from django.contrib.messages import SUCCESS
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.views.generic import FormView
from unittest.mock import patch

from activity_calendar.tests import mock_now
from core.tests.util import suppress_warnings
from utils.testing.view_test_utils import ViewValidityMixin

from surveys.models import Survey, Response
from surveys.forms import SurveyForm
from surveys.views import SurveyFormView


class SurveyFormViewTestCase(ViewValidityMixin, TestCase):
    fixtures = ['test_users', 'test_members', 'surveys/test_surveys']
    base_user_id = 100

    def get_base_url(self):
        return reverse('surveys:fill_in', kwargs={'survey_id': 1})

    def test_class(self):
        self.assertTrue(issubclass(SurveyFormView, FormView))
        self.assertEqual(SurveyFormView.template_name, "surveys/survey_form_page.html")
        self.assertEqual(SurveyFormView.form_class, SurveyForm)

    def test_view_succesful(self):
        self.assertValidGetResponse()

    def test_post_succesful(self):
        response = self.client.post(self.get_base_url(), data={'first-question': 'new-trick'}, follow=True)
        self.assertRedirects(response, reverse("surveys:overview"))

        self.assertHasMessage(response, level=SUCCESS)

    @suppress_warnings
    @patch('django.utils.timezone.now', side_effect=mock_now(datetime.datetime(2022, 2, 1, 0, 0)))
    def test_start_date_validation(self, mock_tz):
        Survey.objects.filter(id=1).update(start_date=timezone.make_aware(datetime.datetime(2022, 3, 1, 0, 0)))
        self.assertGetResponseNotFound()
        Survey.objects.filter(id=1).update(start_date=timezone.make_aware(datetime.datetime(2022, 1, 1, 0, 0)))
        self.assertValidGetResponse()

    @suppress_warnings
    @patch('django.utils.timezone.now', side_effect=mock_now(datetime.datetime(2022, 2, 1, 0, 0)))
    def test_end_date_validation(self, mock_tz):
        Survey.objects.filter(id=1).update(end_date=timezone.make_aware(datetime.datetime(2022, 3, 1, 0, 0)))
        response = self.assertValidGetResponse()
        self.assertTemplateUsed(response, "surveys/survey_form_page.html")

        # The expired template should be shown, not the normal form page
        Survey.objects.filter(id=1).update(end_date=timezone.make_aware(datetime.datetime(2022, 1, 1, 0, 0)))
        response = self.assertValidGetResponse()
        self.assertTemplateUsed(response, "surveys/survey_expired.html")
        self.assertIn('survey', response.context.keys())
        self.assertIn('response', response.context.keys())
