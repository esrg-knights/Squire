from django.shortcuts import render, get_object_or_404, redirect
from rest_framework import routers, viewsets
from rest_framework.views import APIView, Response

from .models import Achievement
from .serializers import AchievementSerializer


def viewAllAchievements(request):
    serializer = AchievementSerializer(Achievement.objects.all(), many=True)
    return render(request, 'achievements/view-all-achievements.html', {"achievements": serializer.data})

def viewSpecificAchievement(request, id):
    pAchievement = get_object_or_404(Achievement, pk=id)
    serializer = AchievementSerializer(pAchievement)
    return render(request, 'achievements/view-Achievement.html', serializer.data)
