from django.views.generic import TemplateView

from user_interaction.accountcollective import AccountViewMixin

from achievements.models import Category
from achievements.serializers import CategorySerializer, AchievementSortType


class AchievementAccountView(AccountViewMixin, TemplateView):
    template_name = "achievements/view_achievements_user.html"

    def get_context_data(self, **kwargs):
        serializer = CategorySerializer(
            Category.objects.all(),
            many=True,
            context={
                "user_id": self.request.user.id,
                "sort_type": AchievementSortType.ACHIEVEMENTSORT_LATEST_UNLOCK_DATE,
            },
        )

        context = super(AchievementAccountView, self).get_context_data()
        context.update(
            {
                "categories": serializer.data,
                "request_user_id": self.request.user.id,
                "show_claimants": True,
            }
        )
        return context
