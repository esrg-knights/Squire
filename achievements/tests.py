from django.test import TestCase, Client
from .serializers import AchievementSerializer, CategorySerializer
from .models import Achievement, Category

# Create your tests here.
class TestCaseAchievementFrontEndViews(TestCase):
    @classmethod

    def setUp(self):
        # This runs 1x per testcase (before) within this class
        self.client = Client()

    def test_case_view_all_achievements(self):
         #This is a TestCase
         testSerializer = {"achievements" : (AchievementSerializer(Achievement.objects.all(),many=True)).data}
         response = self.client.get('/achievements/' , data=testSerializer, secure=True)
         self.assertEqual(response.status_code, 200)

    # def test_case_view_specific_achievement(self):
    #      testSerializer = (AchievementSerializer(Achievement.objects.all().first(),many=True)).data
    #      response = self.client.get('/achievements/1' , data=testSerializer, secure=True)
    #      self.assertEqual(response.status_code, 200)

    def test_case_view_all_categories(self):
         testSerializer = {"categories" : (CategorySerializer(Category.objects.all(),many=True)).data}
         response = self.client.get('/achievements/categories/' , data=testSerializer, secure=True)
         self.assertEqual(response.status_code, 200)

    # def test_case_view_specific_category(self):
    #      testSerializer = (CategorySerializer(Category.objects.all().first(),many=True)).data
    #      response = self.client.get('/achievements/categories/1' , data=testSerializer, secure=True)
    #
    #      self.assertEqual(response.status_code, 200)

# class TestCaseAchievementModels(TestCase):
#     @classmethod
#     #def setUpTestData(self):
#         # dit runt in totaal maar 1x (voor alle tests binnen deze class)
#
#     def setUp(self):
#         # Dit runt 1x per testcase (ervoor) binnen deze class
#         #self.client = Client()
#         self.categoryData = {
#             "name": "ZG-Category",
#             "description": "Boardgames-description",
#         }
#         self.category = Category.objects.create(**self.categoryData)
#
#         # Save the models
#         Category.save(self.category)
#
#     def test_case_get_category_name(self):
#          # dit is een testcase
#          self.name = self.category.name
#          self.assertIsNotNone(self.name)
#          self.category.delete()
#          # No category should exist if it's deleted
#          self.assertIsNone(Category.objects.all().first())
