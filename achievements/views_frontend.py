from django.shortcuts import render, get_object_or_404, redirect
from rest_framework import routers, viewsets
from rest_framework.views import APIView, Response

from .models import Achievement, Category
from .serializers import AchievementSerializer, CategorySerializer


def viewAllAchievements(request):
    serializer = AchievementSerializer(Achievement.objects.all(), many=True)
    return render(request, 'achievements/view-all-achievements.html', {"achievements": serializer.data})

def viewSpecificAchievement(request, id):
    pAchievement = get_object_or_404(Achievement, pk=id)
    serializer = AchievementSerializer(pAchievement)
    return render(request, 'achievements/view-Achievement.html', serializer.data)

def viewAllCategories(request):
    serializer = CategorySerializer(Category.objects.all(), many=True)
    return render(request, 'achievements/view-all-categories.html', {"categories": serializer.data})

def viewSpecificCategory(request, id):
    pCategory = get_object_or_404(Category, pk=id)
    serializer = CategorySerializer(pCategory)
    return render(request, 'achievements/view-Category.html', {"category": serializer.data, "related_achievements": pCategory.related_achievements.all()})
