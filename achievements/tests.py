from django.test import TestCase, Client
from .serializers import AchievementSerializer, CategorySerializer
from .models import Achievement, Category
from membership_file.models import Member
from membership_file.serializers import MemberSerializer

# Create your tests here.
class TestCaseAchievementFrontEndViews(TestCase):

    def setUp(self):
        # This runs 1x per testcase (before) within this class
        self.client = Client()

        # Make a Category
        self.categoryData = {
            "name": "ZG-Category",
            "description": "Boardgames-description",
        }
        self.category = Category.objects.create(**self.categoryData)

        # Save the model
        Category.save(self.category)

        # Make an Achievement
        self.achievementData = {
            "category": Category.objects.all().first(),
            "name": "Achievement_name",
            "description": "Achievement_description",
        }
        self.achievement = Achievement.objects.create(**self.achievementData)
        Achievement.save(self.achievement)

        # Make a Member
        self.memberData = {
            "first_name": "Fantasy",
            "last_name": "Court",
            "date_of_birth": "1970-01-01",
            "email": "info@fantasycourt.nl",
            "street": "Veld",
            "house_number": "5",
            "city": "Eindhoven",
            "country": "The Netherlands",
            "postal_code": "5612 AH",
            "member_since": "1970-01-01",
        }
        self.member = Member.objects.create(**self.memberData)
        Member.save(self.member)

    #Tests if the page that shows all the achievement-categories can be accessed
    def test_case_view_all_categories(self):
         testSerializer = {"categories" : (CategorySerializer(Category.objects.all(),many=True)).data}
         response = self.client.get('/achievements/categories/', data=testSerializer, secure=True)
         self.assertEqual(response.status_code, 200)

    #Tests if the page that shows the information an achievement-category has can be accessed
    def test_case_view_specific_category(self):
         testSerializer = (CategorySerializer(Category.objects.all().first())).data
         response = self.client.get('/achievements/categories/1', data=testSerializer, follow=True, secure=True)

         self.assertEqual(response.status_code, 200)

    #Tests if the page that shows all the achievements can be accessed
    def test_case_view_all_achievements(self):
        #This is a TestCase
        testSerializer = {"achievements" : (AchievementSerializer(Achievement.objects.all(),many=True)).data}
        response = self.client.get('/achievements/', data=testSerializer, secure=True)
        self.assertEqual(response.status_code, 200)

    #Tests if the page that shows the information an achievement has can be accessed
    def test_case_view_specific_achievement(self):
        testSerializer = (AchievementSerializer(Achievement.objects.all().first())).data
        response = self.client.get('/achievements/1', data=testSerializer, follow=True, secure=True)
        self.assertEqual(response.status_code, 200)

    #Tests if the page that shows the achievements a member has can be accessed
    def test_case_view_specific_member(self):
        response = self.client.get('/achievements/members/1', data=self.memberData, follow=True, secure=True)
        self.assertEqual(response.status_code, 200)
