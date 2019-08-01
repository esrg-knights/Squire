from django.shortcuts import render, get_object_or_404, redirect
from rest_framework import routers, viewsets
from rest_framework.views import APIView, Response

from .models import Achievement
from .serializers import AchievementSerializer


def viewAllAchievements(request):
    serializer = AchievementSerializer(Achievement.objects.all(), many=True)
    return render(request, 'achievements/view-all-achievements.html', {"achievements": serializer.data})
