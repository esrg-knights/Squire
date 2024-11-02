from django.contrib.auth.models import Permission
from django.db.models import Q

from utils.viewcollectives import *
from utils.auth_utils import get_perm_from_name

from committees.models import AssociationGroup
from committees.utils import user_in_association_group
from committees.options import settings_options_registry


class CommitteeBaseConfig(ViewCollectiveConfig):
    """Configurations for additional tabs on committee pages"""

    setting_option_classes = []
    url_keyword = None
    name = None
    url_name = None
    group_requires_permission = None

    """ Namespace for url. Can be left none. If not left none, know that url navigation will go like:
    committees:<namespace>:url_name
    """
    namespace = None

    def __init_subclass__(cls, **kwargs):
        # Register the options as defined in the subclass
        for option in cls.setting_option_classes:
            # Duplicate the permissions to the options
            if cls.group_requires_permission:
                option.group_requires_permission = cls.group_requires_permission
            settings_options_registry.register(option)

    def is_accessible_for(self, request, association_group=None) -> bool:
        if not super(CommitteeBaseConfig, self).is_accessible_for(request):
            return False

        if not user_in_association_group(request.user, association_group):
            return False

        return self.check_group_access(association_group)

    def check_group_access(self, association_group):
        """Checks whether the group has access"""
        if self.group_requires_permission is not None:
            return association_group.has_perm(self.group_requires_permission)
        return True

    def enable_access(self, association_group: AssociationGroup):
        """Adjusts the association_group so that it can access this collective"""
        association_group.permissions.add(get_perm_from_name(self.group_requires_permission))

    def disable_access(self, association_group: AssociationGroup):
        """Adjusts the association_group so that it can no longer access this collective"""
        association_group.site_group.permissions.remove(get_perm_from_name(self.group_requires_permission))
        association_group.permissions.remove(get_perm_from_name(self.group_requires_permission))

    def is_default_for_group(self, association_group: AssociationGroup):
        """Whether this collective is a default"""
        # Later PR will replace this to default for certain types of groups
        return self.group_requires_permission is None

    def get_local_quicklinks(self, association_group):
        """Returns a list of dicts with local shortcut instances
        ('name': X, 'url': X)
        """
        return []

    def get_urls(self):
        raise NotImplementedError

    def get_absolute_url(self, association_group, **url_kwargs):
        url_kwargs.setdefault("group_id", association_group)
        return super(CommitteeBaseConfig, self).get_absolute_url(**url_kwargs)


registry = ViewCollectiveRegistry("committees", "committee_pages", config_class=CommitteeBaseConfig)
