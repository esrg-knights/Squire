from datetime import datetime
from django.core.exceptions import ValidationError
from django.test import TestCase

from surveys.models import Survey, Response, Question, Answer


class SurveyTestCase(TestCase):
    fixtures = ['test_users', 'test_members', 'surveys/test_surveys']

    def test_str(self):
        survey = Survey.objects.get(id=1)
        self.assertEqual(survey.name, str(survey))

    def test_clean_end_date(self):
        survey = Survey(
            name="test survey"
        )
        self.assertIsClean(survey)
        survey.end_date = datetime(2022, 1, 20, 12, 0, 0)
        self.assertIsClean(survey)
        survey.start_date = datetime(2022, 1, 22, 12, 0, 0)
        # End date can not be before start date
        try:
            survey.clean()
        except ValidationError as v:
            self.assertIn('end_date', v.error_dict.keys())
        except:
            raise AssertionError("Clean did not raise validation error on end date before start date")

    def assertIsClean(self, object):
        try:
            object.clean()
        except ValidationError as e:
            raise AssertionError(
                f'{object.__class__.__name__} was not clean: {e.message}'
            )

class ResponseTestCase(TestCase):
    fixtures = ['test_users', 'test_members', 'surveys/test_surveys']



class QuestionTestCase(TestCase):
    fixtures = ['test_users', 'test_members', 'surveys/test_surveys']



class AnswerTestCase(TestCase):
    fixtures = ['test_users', 'test_members', 'surveys/test_surveys']
