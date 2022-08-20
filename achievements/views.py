from django.views.generic import TemplateView, ListView
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_safe

from .models import Category, Achievement


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


class AllAchievementsView(ListView):
    template_name = 'achievements/view_achievements_all.html'
    model = Achievement

    def get_context_data(self, **kwargs):
        context = super().get_context_data()

    def get_queryset(self) -> _SupportsPagination[_M]:
        return super().get_queryset().filter(is_public=True)
    
