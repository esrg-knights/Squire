from django.contrib.messages import SUCCESS
from django.test import TestCase
from django.urls import reverse
from django.views.generic import FormView

from utils.testing.view_test_utils import ViewValidityMixin

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
