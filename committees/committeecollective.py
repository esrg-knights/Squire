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
    requires_permission = None

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
        if self.requires_permission is not None:
            app_label, codename = self.requires_permission.split('.', maxsplit=1)
            if not Permission.objects.filter(
                content_type__app_label=app_label,
                codename=codename,
                group__associationgroup=association_group
            ):  return False

        return True

    def get_local_quicklinks(self, association_group):
        """ Returns a list of dicts with local shortcut instances
        ('name': X, 'url': X)
        """
        return []


class AssociationGroupMixin(ViewCollectiveViewMixin):
    """ Mixin that stores the retrieved group from the url group_id keyword. Also verifies user is part of that group """
    association_group = None
    selected_tab_name = None

    def setup(self, request, *args, **kwargs):
        self.association_group = get_object_or_404(AssociationGroup, id=kwargs['group_id'])
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
        context['association_group'] = self.association_group
        return context

    def _get_tab_url(self, url_name, **url_kwargs):
        """ Returns the url for the tab. Interject url_kwargs to add extra perameters"""
        url_kwargs['group_id'] = self.association_group.id
        return super(AssociationGroupMixin, self)._get_tab_url(url_name, **url_kwargs)


registry = AccountRegistry('committees', 'committee_pages', config_class=CommitteeBaseConfig)
