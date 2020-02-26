from .models import Achievement, Category
from rest_framework import serializers
from django.contrib.auth.models import User


# Dictionary representation of an Achievement
# Includes a 'claimed' field representing whether the currently logged in
# user has the given achievement
class AchievementSerializer(serializers.ModelSerializer):
    claimed = serializers.SerializerMethodField('earned_by_current_user')
    claimants = serializers.SerializerMethodField('get_all_claimants')
    
    class Meta:
        model = Achievement
        fields = ('name', 'description', 'claimed', 'claimants')
        depth = 0
    
    # Adds a field representing whether the achievement was
    # claimed by the logged in user
    def earned_by_current_user(self, obj):
        user_id = self.context.get("user_id")
        obtain_self_earned = self.context.get("obtain_self_earned")
        if obtain_self_earned and user_id and obj.claimants.filter(id=user_id).exists():
            return True
        return False
    
    # Gets all claimants of an achievement
    def get_all_claimants(self, obj):
        obtain_claimants = self.context.get("obtain_claimants")
        if obtain_claimants:
            # Obtain user
            pUser = User.objects.filter(id=self.context.get("user_id")).first()
            has_permission_to_obtain_claimants = obj.user_can_view_claimants(pUser)

            # User is actually allowed to view claimants
            if has_permission_to_obtain_claimants:
                return [user.get_display_name() for user in User.objects.filter(claimed_achievements__id=obj.id)]
        return []

# Dictionary representation of a Category
# Includes all achievements from that Category
class CategorySerializer(serializers.ModelSerializer):
    achievements = AchievementSerializer(source='related_achievements', many=True)

    class Meta:
        model = Category
        fields = ("name", "description", "achievements")
        depth = 1
