from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied

from utils.viewcollectives import *

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
            raise PermissionDenied()

        # Check group permission
        if self.group_requires_permission is not None:
            app_label, codename = self.group_requires_permission.split('.', maxsplit=1)
            if not Permission.objects.filter(       # Check for django group permissions
                content_type__app_label=app_label,
                codename=codename,
                group__associationgroup=association_group
            ).exists() and not Permission.objects.filter( # Check for associationgroup permissions
                content_type__app_label=app_label,
                codename=codename,
                associationgroup=association_group
            ).exists():  return False

        return True

    def get_local_quicklinks(self, association_group):
        """ Returns a list of dicts with local shortcut instances
        ('name': X, 'url': X)
        """
        return []


registry = ViewCollectiveRegistry('committees', 'committee_pages', config_class=CommitteeBaseConfig)
