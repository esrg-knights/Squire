from django.test import TestCase


from utils.testing import FormValidityMixin

from surveys.forms import SurveyForm
from surveys.models import Survey, Response, Answer


class SurveyFormTestCase(FormValidityMixin, TestCase):
    fixtures = ['test_users', 'test_members', 'surveys/test_surveys']
    form_class = SurveyForm

    def setUp(self):
        self.survey = Survey.objects.get(id=1)
        self.response = Response.objects.get(id=1)

    def get_form_kwargs(self, **kwargs):
        kwargs.setdefault('survey', self.survey)
        kwargs.setdefault('response', self.response)
        return super(SurveyFormTestCase, self).get_form_kwargs(
            **kwargs
        )

    def test_input_assertions(self):
        """ Test form init input assertions """
        # This should throw no errors
        self.build_form({})

        with self.assertRaises(AssertionError):
            self.build_form({}, survey=None)

        with self.assertRaises(AssertionError):
            self.build_form({}, response=None)

    def test_field_creation_empty(self):
        form = self.build_form({}, response=Response(survey_id=1, member_id=3))
        self.assertEqual(len(form.fields.keys()), 4)
        self.assertIn('first-question', form.fields.keys())
        self.assertIn('another-question', form.fields.keys())
        self.assertIn('int-question', form.fields.keys())
        self.assertIn('choice-question', form.fields.keys())

        self.assertEqual(form.fields['first-question'].initial, '')
        self.assertEqual(form.fields['int-question'].initial, '')
        self.assertEqual(form.fields['choice-question'].initial, '')

    def test_field_creation_from_db(self):
        form = self.build_form({})
        self.assertEqual(len(form.fields.keys()), 4)
        self.assertIn('first-question', form.fields.keys())
        self.assertIn('another-question', form.fields.keys())
        self.assertIn('int-question', form.fields.keys())
        self.assertIn('choice-question', form.fields.keys())

        # Check that the starting values are the same as what is defined in the fixture
        self.assertEqual(form.fields['first-question'].initial, 'Hooplala')
        self.assertEqual(form.fields['int-question'].initial, '8')
        self.assertEqual(form.fields['choice-question'].initial, 1) # uses relative position in the choice list

    def test_required_fields(self):
        """ Tests that a required question is required """
        self.assertFormHasError({}, 'required')
        self.assertFormValid({'first-question': "new answer"})

    def test_saving_update_response(self):
        fixture_update_date = self.response.last_updated_on

        form = self.assertFormValid({'first-question': 'new-trick', 'int-question': '14'})
        form.save()
        self.assertEqual(Answer.objects.get(response=self.response, question_id=1).value, 'new-trick')
        self.assertEqual(Answer.objects.get(response=self.response, question_id=3).value, '14')
        # Assert that the last update date is updated
        self.assertGreater(self.response.last_updated_on, fixture_update_date)

    def test_saving_new_response(self):
        form = self.assertFormValid(
            {'first-question': 'new response answer'},
            response=Response(survey=self.survey, member_id=3))
        form.save()
        self.assertEqual(Answer.objects.get(response_id=3, question_id=1).value, 'new response answer')

