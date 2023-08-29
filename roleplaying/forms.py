from core.forms import MarkdownForm
from roleplaying.models import RoleplayingSystem


class RoleplayingSystemUpdateForm(MarkdownForm):
    class Meta:
        model = RoleplayingSystem
        exclude = ["is_public"]


class RoleplayingSystemAdminForm(MarkdownForm):
    class Meta:
        model = RoleplayingSystem
        fields = "__all__"
