from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView

from membership_file.util import MembershipRequiredMixin
from user_interaction.account_pages.mixins import AccountViewMixin

from achievements.models import Category
from achievements.serializers import CategorySerializer, AchievementSortType


class AchievementAccountView(MembershipRequiredMixin, AccountViewMixin, TemplateView):
    template_name = "achievements/view_achievements_user.html"
    selected_tab_name = 'tab_achievements'

    def get_context_data(self, **kwargs):
        serializer = CategorySerializer(Category.objects.all(), many=True, context={
            'user_id': self.request.user.id,
            'sort_type': AchievementSortType.ACHIEVEMENTSORT_LATEST_UNLOCK_DATE,
        })

        context = super(AchievementAccountView, self).get_context_data()
        context.update({
            "categories": serializer.data,
            "request_user_id": self.request.user.id,
            "show_claimants": True,
        })
        return context
