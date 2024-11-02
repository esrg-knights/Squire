from django.core.exceptions import PermissionDenied, ImproperlyConfigured

from utils.viewcollectives import *


class AssociationGroupMixin(ViewCollectiveViewMixin):
    """Mixin that stores the retrieved group from the url group_id keyword. Also verifies user is part of that group"""

    association_group = None
    selected_tab_name = None

    def setup(self, request, *args, group_id, **kwargs):
        self.association_group = group_id
        return super(AssociationGroupMixin, self).setup(request, *args, **kwargs)

    def _get_other_check_kwargs(self):
        """
        Returns a dict with other kwargs for validation checks (e.g. association_group)
        :return:
        """
        return {"association_group": self.association_group}

    def get_context_data(self, **kwargs):
        context = super(AssociationGroupMixin, self).get_context_data(**kwargs)
        context["association_group"] = self.association_group
        context["config"] = self.config
        return context

    def _get_tab_url(self, url_name, **url_kwargs):
        """Returns the url for the tab. Interject url_kwargs to add extra perameters"""
        url_kwargs["group_id"] = self.association_group
        return super(AssociationGroupMixin, self)._get_tab_url(url_name, **url_kwargs)


class AssociationGroupPermissionRequiredMixin:
    group_permissions_required = None

    def dispatch(self, request, *args, **kwargs):
        if self.group_permissions_required is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} is missing the group_permissions_required attribute."
            )
        if isinstance(self.group_permissions_required, str):
            self.group_permissions_required = [self.group_permissions_required]

        for perm in self.group_permissions_required:
            if not self.association_group.has_perm(perm):
                raise PermissionDenied

        return super(AssociationGroupPermissionRequiredMixin, self).dispatch(request, *args, **kwargs)


class GroupSettingsMixin(AssociationGroupMixin):
    settings_option = None

    def setup(self, request, *args, **kwargs):
        super(GroupSettingsMixin, self).setup(request, *args, **kwargs)
        if not self.check_setting_access():
            raise PermissionDenied

    def check_setting_access(self):
        return self.settings_option.check_option_access(self.association_group)

    def get_context_data(self, **kwargs):
        options = sorted(self.config.get_options(self.association_group), key=lambda option: option.order)

        context = super(GroupSettingsMixin, self).get_context_data(**kwargs)
        context["settings_option"] = self.settings_option
        context["options_list"] = options
        return context
