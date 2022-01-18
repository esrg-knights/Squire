from django.core.exceptions import ValidationError
from django.test import TestCase

from surveys.models import Survey, Response, Question, Answer


class SurveyTestCase(TestCase):
    fixtures = ['test_users', 'test_members', 'surveys/test_surveys']

    def test_str(self):
        survey = Survey.objects.get(id=1)
        self.assertEqual(survey.name, str(survey))



class ResponseTestCase(TestCase):
    fixtures = ['test_users', 'test_members', 'surveys/test_surveys']



class QuestionTestCase(TestCase):
    fixtures = ['test_users', 'test_members', 'surveys/test_surveys']



class AnswerTestCase(TestCase):
    fixtures = ['test_users', 'test_members', 'surveys/test_surveys']
