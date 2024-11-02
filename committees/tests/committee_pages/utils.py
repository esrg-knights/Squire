from django.contrib.auth.models import Group
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

from utils.testing.view_test_utils import ViewValidityMixin

from committees.models import AssociationGroup


class AssocationGroupTestingMixin(ViewValidityMixin):
    """Mixin for testing AssociationGroup Views
    Use 'association_group_id' to set the association_group for testing with a group on the database. Otherwise a
    new instance will be made with type defined in 'association_group_type'
    url_name is url name excluding the committees namespace
    Group will automatically be given permissions defined in group_permissions_required

    """

    association_group_id = None
    association_group_type = None
    url_name = None
    group_permissions_required = None

    def __init__(self, *args, **kwargs):
        self.association_group = None
        super(AssocationGroupTestingMixin, self).__init__(*args, **kwargs)

    def setUp(self):
        super(AssocationGroupTestingMixin, self).setUp()
        if self.association_group_id is None:
            group = Group.objects.create(name=f"{self.__class__.__name__}_group")
            self.association_group = AssociationGroup.objects.create(
                site_group=group, type=self.association_group_type or AssociationGroup.COMMITTEE
            )
            self.association_group.members.add(self.user.member)
        else:
            self.association_group = AssociationGroup.objects.get(id=self.association_group_id)

        if self.group_permissions_required:
            if isinstance(self.group_permissions_required, str):
                self.group_permissions_required = (self.group_permissions_required,)

            for perm_name in self.group_permissions_required:
                self._set_group_perm(perm_name, self.association_group)

    def _set_group_perm(self, perm_name, group: AssociationGroup):
        group.permissions.add(self._get_perm_by_name(perm_name))
        # Delete the group permission cache
        if group.site_group is not None:
            try:
                del group.site_group._group_perm_cache
                del group.site_group._perm_cache
            except AttributeError:
                pass

    def get_base_url(self, **url_kwargs):
        if self.url_name is None:
            raise ImproperlyConfigured(f"'url_name' was not defined on {self.__class__.__name__}")
        return reverse("committees:" + self.url_name, kwargs=self.get_url_kwargs(**url_kwargs))

    def get_url_kwargs(self, **kwargs):
        kwargs.setdefault("group_id", self.association_group)
        return kwargs
