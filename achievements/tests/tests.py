from django.test import TestCase

from achievements.models import Achievement, Category
from core.tests.util import check_http_response, TestPublicUser, TestAccountUser, check_http_response_with_login_redirect


class TestCaseAchievementFrontEndViews(TestCase):
    fixtures = TestAccountUser.get_fixtures()

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
        check_http_response(self, '/achievements', 'get', TestPublicUser)

    def test_account_achievements(self):
        check_http_response_with_login_redirect(self, '/account/achievements', 'get')


