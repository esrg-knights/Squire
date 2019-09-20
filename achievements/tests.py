from django.test import TestCase, Client
from .serializers import AchievementSerializer
from .models import Achievement

# Create your tests here.
class TestCaseAchievementFrontEndViews(TestCase):
    @classmethod

    def setUp(self):
        # Dit runt 1x per testcase (ervoor) binnen deze class
        self.client = Client()

    def test_case_view_all_achievements(self):
         #dit is een testcase
         testSerializer = {"achievements" : (AchievementSerializer(Achievement.objects.all(),many=True)).data}
         response = self.client.get('/achievements/' , data=testSerializer, secure=True)

         self.assertEqual(response.status_code, 200)
