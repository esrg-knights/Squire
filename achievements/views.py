from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.http import require_safe

from .models import Achievement, Category
from .serializers import AchievementSerializer, CategorySerializer

@require_safe
def viewAllAchievements(request):
    serializer = AchievementSerializer(Achievement.objects.all(), many=True)
    return render(request, 'achievements/view-all-achievements.html', {"achievements": serializer.data})

@require_safe
def viewSpecificAchievement(request, id):
    pAchievement = get_object_or_404(Achievement, pk=id)
    serializer = AchievementSerializer(pAchievement)
    return render(request, 'achievements/view-achievement.html', serializer.data)

@require_safe
def viewAllCategories(request):
    serializer = CategorySerializer(Category.objects.all(), many=True)
    return render(request, 'achievements/view-all-categories.html', {"categories": serializer.data})

@require_safe
def viewSpecificCategory(request, id):
    pCategory = get_object_or_404(Category, pk=id)
    serializer = CategorySerializer(pCategory)
    return render(request, 'achievements/view-category.html', {"category": serializer.data, "related_achievements": pCategory.related_achievements.all()})

@require_safe
def viewSpecificMember(request, id):
    pMember = get_object_or_404(Member, pk=id)
    serializer = MemberSerializer(pMember)
    return render(request, 'achievements/view-member.html', {"member": serializer.data, "claimed_achievements": pMember.claimed_achievements.all()})


# View user Achievements Page
@require_safe
@login_required
def viewAchievementsUser(request):
    serializer = CategorySerializer(Category.objects.all(), many=True, context={
        'user_id': request.user.id
    })

    return render(request, 'achievements/view_achievements_user.html', {
        "categories": serializer.data
    })

# View all Achievements Page
@require_safe
def viewAchievementsAll(request):
    show_claimants = Achievement.user_can_view_claimants(request.user)
    serializer = CategorySerializer(Category.objects.all(), many=True, context={
        "obtain_claimants": show_claimants,
    })
    
    return render(request, 'achievements/view_achievements_all.html', {
        "categories": serializer.data,
        "show_claimants": show_claimants,
    })
