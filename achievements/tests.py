from django.test import TestCase, Client

from .serializers import AchievementSerializer, CategorySerializer
from .models import Achievement, Category

from membership_file.models import Member
from membership_file.serializers import MemberSerializer
from core.tests import checkAccessPermissions, PermissionLevel

# Create your tests here.
class TestCaseAchievementFrontEndViews(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):

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


    def test_public_achievements(self):
        checkAccessPermissions(self, '/achievements', 'get', PermissionLevel.LEVEL_PUBLIC)
    
    def test_account_achievements(self):
        checkAccessPermissions(self, '/account/achievements', 'get', PermissionLevel.LEVEL_USER)


    