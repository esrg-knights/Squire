from .models import Achievement
from rest_framework import serializers


# The MemberSerializer converts the Member model to a Python dictionary
class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = "__all__"
        depth = 0
