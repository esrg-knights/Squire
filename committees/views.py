
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404


class GroupMixin:
    """ Mixin that stores the retrieved group from the url group_id keyword. Also verifies user is part of that group """
    group = None

    def dispatch(self, request, *args, **kwargs):
        self.group = get_object_or_404(Group, id=self.kwargs['group_id'])
        if self.group not in self.request.user.groups.all():
            raise PermissionDenied()

        return super(GroupMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(GroupMixin, self).get_context_data(**kwargs)
        context['group'] = self.group
        return context