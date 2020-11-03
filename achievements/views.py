from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from core.models import ExtendedUser as User
from django.views.decorators.http import require_safe

from .models import Achievement, Category
from .serializers import AchievementSerializer, CategorySerializer, AchievementSortType


# View user Achievements Page
@require_safe
@login_required
def viewAchievementsUser(request):
    serializer = CategorySerializer(Category.objects.all(), many=True, context={
        'user_id': request.user.id,
        'sort_type': AchievementSortType.ACHIEVEMENTSORT_LATEST_UNLOCK_DATE,
    })

    return render(request, 'achievements/view_achievements_user.html', {
        "categories": serializer.data,
        "request_user_id": request.user.id,
        "show_claimants": True,
    })

# View all Achievements Page
@require_safe
def viewAchievementsAll(request):
    show_claimants = request.user.has_perm('achievements.can_view_claimants')
    serializer = CategorySerializer(Category.objects.all(), many=True, context={
        "obtain_claimants": show_claimants,
    })

    return render(request, 'achievements/view_achievements_all.html', {
        "categories": serializer.data,
        "show_claimants": show_claimants,
        "request_user_id": request.user.id,
    })
