from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from utils.viewcollectives import *

from committees.utils import user_in_association_group
from committees.models import AssociationGroup


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


def _wrap_association_group_for_context(association_group: AssociationGroup):
    """ Update the association_group with template optimised attributes """
    for group_type in AssociationGroup.GROUPTYPES:
        # Allow the type to be retrieved by selecting the type constant (e.g. association_group.GUILD)
        setattr(
            association_group,
            group_type[1].upper(),
            association_group.type == group_type[0]
        )
    return association_group



class AssociationGroupMixin(ViewCollectiveViewMixin):
    """ Mixin that stores the retrieved group from the url group_id keyword. Also verifies user is part of that group """
    association_group = None
    selected_tab_name = None

    def setup(self, request, *args, group_id: AssociationGroup, **kwargs):
        self.association_group = group_id
        return super(AssociationGroupMixin, self).setup(request, *args, **kwargs)

    def _get_other_check_kwargs(self):
        """
        Returns a dict with other kwargs for validation checks (e.g. association_group)
        :return:
        """
        return {
            'association_group': self.association_group
        }

    def get_context_data(self, **kwargs):
        context = super(AssociationGroupMixin, self).get_context_data(**kwargs)
        context['association_group'] = _wrap_association_group_for_context(self.association_group)
        return context

    def _get_tab_url(self, url_name, **url_kwargs):
        """ Returns the url for the tab. Interject url_kwargs to add extra perameters"""
        url_kwargs['group_id'] = self.association_group
        return super(AssociationGroupMixin, self)._get_tab_url(url_name, **url_kwargs)


registry = ViewCollectiveRegistry('committees', 'committee_pages', config_class=CommitteeBaseConfig)
