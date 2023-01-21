from django.contrib.auth.models import Permission
from django.shortcuts import get_object_or_404

from utils.viewcollectives import *
from utils.auth_utils import get_perm_from_name

from committees.models import AssociationGroup
from committees.utils import user_in_association_group


class CommitteeBaseConfig(ViewCollectiveConfig):
    """ Configurations for additional tabs on committee pages """
    url_keyword = None
    name = None
    url_name = None
    group_requires_permission = None

    """ Namespace for url. Can be left none. If not left none, know that url navigation will go like:
    committees:<namespace>:url_name
    """
    namespace = None

    def check_access_validity(self, request, association_group=None):
        if not super(CommitteeBaseConfig, self).check_access_validity(request):
            return False

        if not user_in_association_group(request.user, association_group):
            return False

        return self.check_group_access(association_group)

    def check_group_access(self, association_group):
        """ Checks whether the group has access """
        if self.group_requires_permission is not None:
            try:
                perm = get_perm_from_name(self.group_requires_permission)
            except Permission.DoesNotExist:
                raise KeyError(f"{self.__class__} is configured incorrectly. "
                               f"{self.group_requires_permission} is not a valid permission. ")
            else:
                if not perm.group_set.filter(associationgroup=association_group).exists():
                    return False
        return True

    def enable_access(self, association_group: AssociationGroup):
        """ Adjusts the association_group so that it can access this collective """
        association_group.site_group.permissions.add(
            get_perm_from_name(self.group_requires_permission)
        )

    def disable_access(self, association_group: AssociationGroup):
        """ Adjusts the association_group so that it can no longer access this collective """
        association_group.site_group.permissions.remove(
            get_perm_from_name(self.group_requires_permission)
        )

    def is_default_for_group(self, association_group: AssociationGroup):
        """ Whether this collective is a default """
        # Later PR will replace this to default for certain types of groups
        return self.group_requires_permission is None

    def get_local_quicklinks(self, association_group):
        """ Returns a list of dicts with local shortcut instances
        ('name': X, 'url': X)
        """
        return []


registry = ViewCollectiveRegistry('committees', 'committee_pages', config_class=CommitteeBaseConfig)
