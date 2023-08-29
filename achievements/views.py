from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_safe

from .models import Category
from .serializers import CategorySerializer, AchievementSortType


# View all Achievements Page
@require_safe
def viewAchievementsAll(request):
    show_claimants = request.user.has_perm("achievements.can_view_claimants")
    serializer = CategorySerializer(
        Category.objects.all(),
        many=True,
        context={
            "obtain_claimants": show_claimants,
        },
    )

    return render(
        request,
        "achievements/view_achievements_all.html",
        {
            "categories": serializer.data,
            "show_claimants": show_claimants,
            "request_user_id": request.user.id,
        },
    )
