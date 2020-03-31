from rest_framework import serializers
from django.db.models import Count, Max, When, Case

from core.models import ExtendedUser as User
from .models import Achievement, Category, Claimant

from enum import Enum

# Enumeration that specifies sorting options for achievements
class AchievementSortType(Enum):
    ACHIEVEMENTSORT_DEFAULT = 1
    ACHIEVEMENTSORT_LATEST_UNLOCK_DATE = 2
    ACHIEVEMENTSORT_MOST_NUM_CLAIMANTS = 3


# Obtains the string that can be used to obtain the sort order of the claimants
def get_claimant_sort(achievement):
    sort_str = ""
    if not achievement.claimants_sort_ascending:
        sort_str += "-"
    sort_str += achievement.claimants_sort_field
    return sort_str


# Dictionary representation of an Achievement
# Includes a 'claimed' field representing whether the currently logged in
# user has the given achievement
class AchievementSerializer(serializers.ModelSerializer):
    claimants = serializers.SerializerMethodField('get_all_claimants')
    claimant_count = serializers.SerializerMethodField('get_num_claimants')

    class Meta:
        model = Achievement
        fields = ('id', 'name', 'description', 'unlocked_text', 'image',
            'claimants', 'claimants_sort_field', 'claimants_sort_ascending',
            'claimant_count')
        depth = 0
    
    # Count number of claimants
    def get_num_claimants(self, obj):
        return Claimant.objects.filter(achievement__id=obj.id).count()
    
    # Gets claimants of an achievement
    def get_all_claimants(self, obj):
        show_claimants = self.context.get("obtain_claimants")
        if show_claimants:
            return ClaimantSerializer(
                Claimant.objects.filter(achievement__id=obj.id)
                    .order_by(get_claimant_sort(obj), '-date_unlocked'),
                many=True).data
        
        user_id = self.context.get("user_id")
        if user_id:
            return ClaimantSerializer(
                Claimant.objects.filter(achievement__id=obj.id, user__id=user_id)
                    .order_by(get_claimant_sort(obj), '-date_unlocked'),
                many=True).data

        return []

class ClaimantSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField('get_user_display_name')
    user_id = serializers.SerializerMethodField('get_current_user_id')
    date_unlocked = serializers.DateField(format="%d %b %Y")

    class Meta:
        model = Claimant
        fields = ('name', 'date_unlocked', 'extra_data_1', 'extra_data_2', 'extra_data_3', 'user_id')
        depth = 0
    
    def get_user_display_name(self, obj):
        return obj.user.get_display_name()
    
    def get_current_user_id(self, obj):
        return obj.user.id


# Dictionary representation of a Category
# Includes all achievements from that Category
class CategorySerializer(serializers.ModelSerializer):
    achievements = serializers.SerializerMethodField('get_all_achievements')

    class Meta:
        model = Category
        fields = ("id", "name", "description", "achievements")
        depth = 1

    # Get achievements with the specified sorting
    def get_all_achievements(self, obj):
        user_id = self.context.get("user_id")
        sort_type = self.context.get("sort_type")
        
        # Sort by name
        if sort_type is None or sort_type == AchievementSortType.ACHIEVEMENTSORT_DEFAULT:
            return AchievementSerializer(Achievement.objects.filter(category__id=obj.id, is_public=True),
                context=self.context, many=True).data                    

        # Sort by latest unlocked date
        if sort_type == AchievementSortType.ACHIEVEMENTSORT_LATEST_UNLOCK_DATE:
            return AchievementSerializer(
                    Achievement.objects.filter(category__id=obj.id, is_public=True)
                            .annotate(latest_unlocked_date=Max(Case(When(claimant__user__id=user_id, then='claimant__date_unlocked'))))
                        .order_by('-latest_unlocked_date', 'name'),
                    context=self.context, many=True).data
        
        # sort_type == AchievementSortType.ACHIEVEMENTSORT_MOST_NUM_CLAIMANTS 
        # Sort by number of claimants
        return AchievementSerializer(
                Achievement.objects.filter(category__id=obj.id, is_public=True)
                    .annotate(num_claimants=Count('claimants'))
                    .order_by('-num_claimants', 'name'),
                context=self.context, many=True).data  
