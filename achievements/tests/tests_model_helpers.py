from django.test import TestCase

from achievements.models import (Achievement, Category, Claimant,
    get_or_create_default_category, get_achievement_image_upload_path)
from core.models import ExtendedUser as User

##################################################################################
# Test the Member model's helper methods
# @since 16 MAR 2020
##################################################################################


# Tests methods related to the Member model
class AchievementModelHelpersTest(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        self.category = Category(id=1, name="TU/e", description="Things at the TU/e")
        self.achievement = Achievement(id=4, name="Wow", description="Do something", category=self.category, image="")

    # Tests the display method of Achievements
    def test_achievement_display(self):
        self.assertEqual(str(self.achievement), "Wow")

    # Tests the display method of Categories
    def test_category_display(self):
        self.assertEqual(str(self.category), "TU/e")

    # Tests the display method of a Claimant
    def test_claimant_display(self):
        claimant = Claimant(achievement=self.achievement, user=User.objects.filter(username="test_user").first())
        self.assertEqual(str(claimant), "Wow unlocked by test_user")

    # Tests if the achievement images are uploaded to the correct location
    def test_image_upload_path(self):
        str_expected_upload_path = "images/achievements/achievement_wow.png"
        str_actual_upload_path = get_achievement_image_upload_path(self.achievement, "some_file_name.png")
        self.assertEqual(str_expected_upload_path, str_actual_upload_path)
