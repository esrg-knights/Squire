from django.test import TestCase
from django.conf import settings

from achievements.models import Achievement, Category, Claimant
from achievements.serializers import (AchievementSerializer, CategorySerializer,
    ClaimantSerializer, AchievementSortType)


# Tests the Achievement-related serializers
class AchievementModelSerializersTest(TestCase):
    fixtures = ['test_users.json', 'test_achievements.json']

    def setUp(self):
        self.category = Category.objects.get(id=1)
        self.achievement = Achievement.objects.get(id=1)
        self.claimant = Claimant.objects.get(id=1)

    # Tests Claimant Serializer
    def test_serializer_claimant(self):
        serializer = ClaimantSerializer(self.claimant, context={})

        self.assertDictEqual(serializer.data, {
            "date_unlocked":    "01 Jan 1970",
            "name":             "test_admin",
            "user_id":          1,
            "extra_data_1":     8,
            "extra_data_2":     "xyz",
            "extra_data_3":     "equal",
        })
    
    # Tests Achievement Seralizer when obtaining all claimants
    def test_serializer_achievement_claimants_all(self):
        serializer = AchievementSerializer(self.achievement, context={
            'obtain_claimants': True,
        })

        self.assertDictEqual(serializer.data, {
            'id':                       1,
            'name':                     "Test",
            'description':              "Be a test user",
            'unlocked_text':            "Unlocked by {0} on {1}",
            'image':                    f"{settings.MEDIA_URL}rubber-duck.jpg",
            'claimants':                ClaimantSerializer(Claimant.objects.filter(achievement__id=self.achievement.id)
                                            .order_by('-date_unlocked'), many=True).data,
            'claimants_sort_field':     "date_unlocked",
            'claimants_sort_ascending': False,
            'claimant_count':           2,
        })

    # Tests Achievement Seralizer when obtaining just a single user's data
    def test_serializer_achievement_claimants_user(self):
        serializer = AchievementSerializer(self.achievement, context={
            'user_id': 1,
        })

        self.assertDictEqual(serializer.data, {
            'id':                       1,
            'name':                     "Test",
            'description':              "Be a test user",
            'unlocked_text':            "Unlocked by {0} on {1}",
            'image':                    f"{settings.MEDIA_URL}rubber-duck.jpg",
            'claimants':                [ClaimantSerializer(self.claimant).data],
            'claimants_sort_field':     "date_unlocked",
            'claimants_sort_ascending': False,
            'claimant_count':           2,
        })
    
    # Tests Achievement Seralizer when obtaining no claimants
    def test_serializer_achievement_claimants_none(self):
        serializer = AchievementSerializer(self.achievement)

        self.assertDictEqual(serializer.data, {
            'id':                       1,
            'name':                     "Test",
            'description':              "Be a test user",
            'unlocked_text':            "Unlocked by {0} on {1}",
            'image':                    f"{settings.MEDIA_URL}rubber-duck.jpg",
            'claimants':                [],
            'claimants_sort_field':     "date_unlocked",
            'claimants_sort_ascending': False,
            'claimant_count':           2,
        })
    
    # Tests the order in which the claimants are passed
    def test_serializer_achievement_claimant_sorting(self):
        # Sorted by date, descending
        serializer = AchievementSerializer(self.achievement, context={
            'obtain_claimants': True,
        })

        claimants = serializer.data.get("claimants")
        self.assertEqual(len(claimants), 2)
        self.assertEqual(claimants[0]['name'], 'test_user')
        self.assertEqual(claimants[1]['name'], 'test_admin')
        
        # Sorted by extra_data_2, descending
        self.achievement.claimants_sort_field = "extra_data_2"
        serializer = AchievementSerializer(self.achievement, context={
            'obtain_claimants': True,
        })

        claimants = serializer.data.get("claimants")
        self.assertEqual(len(claimants), 2)
        self.assertEqual(claimants[0]['name'], 'test_admin')
        self.assertEqual(claimants[1]['name'], 'test_user')

        # Sorted by extra_data_1, ascending
        self.achievement.claimants_sort_field = "extra_data_1"
        self.achievement.claimants_sort_ascending = True
        serializer = AchievementSerializer(self.achievement, context={
            'obtain_claimants': True,
        })
        
        claimants = serializer.data.get("claimants")
        self.assertEqual(len(claimants), 2)
        self.assertEqual(claimants[0]['name'], 'test_admin')
        self.assertEqual(claimants[1]['name'], 'test_user')

        # Sorted by extra_data_3, ascending (which are equal), so fallback to date, descending
        self.achievement.claimants_sort_field = "extra_data_3"
        serializer = AchievementSerializer(self.achievement, context={
            'obtain_claimants': True,
        })

        claimants = serializer.data.get("claimants")
        self.assertEqual(len(claimants), 2)
        self.assertEqual(claimants[0]['name'], 'test_user')
        self.assertEqual(claimants[1]['name'], 'test_admin')

    # Tests the default sorting of a category
    def test_serializer_category_sort_default(self):
        serializer = CategorySerializer(self.category, context={
            'user_id':          1,
            'sort_type':        AchievementSortType.ACHIEVEMENTSORT_DEFAULT,
            'obtain_claimants': False,
        })

        self.assertDictEqual(serializer.data, {
            "id":           1,
            "name":         "Testing",
            "description":  "A Category used for testing!",
            "achievements": AchievementSerializer(Achievement.objects.filter(category__id=self.category.id), 
                many=True, context={
                    'user_id':          1,
                    'obtain_claimants': False
                }).data,
        })
    
    # Tests the latest unlock date sorting of a category
    def test_serializer_category_sort_latest_unlock(self):
        serializer = CategorySerializer(self.category, context={
            'user_id':          1,
            'sort_type':        AchievementSortType.ACHIEVEMENTSORT_LATEST_UNLOCK_DATE,
            'obtain_claimants': False,
        })
        achievements = serializer.data.get('achievements')
        self.assertEqual(len(achievements), 2)
        self.assertEqual(achievements[0]['name'], "Test")
        self.assertEqual(achievements[1]['name'], "The Cooler Test")

    # Tests the highest number of claimants sorting of a category
    def test_serializer_category_sort_most_claimants(self):
        serializer = CategorySerializer(self.category, context={
            'user_id':          1,
            'sort_type':        AchievementSortType.ACHIEVEMENTSORT_MOST_NUM_CLAIMANTS,
            'obtain_claimants': False,
        })
        achievements = serializer.data.get('achievements')
        self.assertEqual(len(achievements), 2)
        self.assertEqual(achievements[0]['name'], "Test")
        self.assertEqual(achievements[1]['name'], "The Cooler Test")

