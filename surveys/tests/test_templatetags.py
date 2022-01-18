from django.test import TestCase

from membership_file.models import Member

from surveys.models import Survey, Response
from surveys.templatetags.survey_tags import get_response_of

class SurveyTagsTestCase(TestCase):
    fixtures = ['test_users', 'test_members', 'surveys/test_surveys']

    def test_response_of(self):
        survey = Survey.objects.get(id=1)
        member_answered = Member.objects.get(id=1)

        self.assertEqual(
            get_response_of(survey, member_answered),
            Response.objects.get(id=1)
        )

        member_not_answered = Member.objects.get(id=3)
        self.assertIsNone(get_response_of(survey, member_not_answered))
