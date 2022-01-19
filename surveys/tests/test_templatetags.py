from django.test import TestCase

from membership_file.models import Member

from surveys.models import Survey, Response, Question, Answer
from surveys.templatetags.survey_tags import get_response_of, get_answer_of

class SurveyTagsTestCase(TestCase):
    fixtures = ['test_users', 'test_members', 'surveys/test_surveys']

    def test_get_response_of(self):
        survey = Survey.objects.get(id=1)
        member_answered = Member.objects.get(id=1)

        self.assertEqual(
            get_response_of(survey, member_answered),
            Response.objects.get(id=1)
        )

        member_not_answered = Member.objects.get(id=3)
        self.assertIsNone(get_response_of(survey, member_not_answered))

    def test_get_answer_of(self):
        question = Question.objects.get(id=1)
        resposne = Response.objects.get(id=1)

        self.assertEqual(
            get_answer_of(question, resposne),
            Answer.objects.get(id=1).value
        )

        # Test for unanswered question of processed response
        resposne = Response.objects.get(id=2)
        self.assertIsNone(get_answer_of(question, resposne))
