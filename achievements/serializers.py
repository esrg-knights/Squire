from .models import Achievement, Category, Claimant
from rest_framework import serializers
from django.contrib.auth.models import User


# Dictionary representation of an Achievement
# Includes a 'claimed' field representing whether the currently logged in
# user has the given achievement
class AchievementSerializer(serializers.ModelSerializer):
    claimants = serializers.SerializerMethodField('get_all_claimants')
    
    class Meta:
        model = Achievement
        fields = ('name', 'description', 'unlocked_text', 'image', 'claimants')
        depth = 0
    
    # Gets claimants of an achievement
    def get_all_claimants(self, obj):
        show_claimants = self.context.get("obtain_claimants")
        if show_claimants:
            return ClaimantSerializer(Claimant.objects.filter(achievement__id=obj.id), many=True).data
        
        user_id = self.context.get("user_id")
        if user_id:
            return ClaimantSerializer(Claimant.objects.filter(achievement__id=obj.id, user__id=user_id), many=True).data

        return []

class ClaimantSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField('get_user_display_name')
    user_id = serializers.SerializerMethodField('get_current_user_id')

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
    achievements = AchievementSerializer(source='related_achievements', many=True)

    class Meta:
        model = Category
        fields = ("name", "description", "achievements")
        depth = 1
