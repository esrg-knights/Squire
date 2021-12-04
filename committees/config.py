from importlib import import_module

from django.apps import apps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission

from .models import AssociationGroup


class CommitteeConfig:
    """ Configurations for additional tabs on committee pages """
    url_keyword = None
    name = None
    tab_select_keyword = None
    url_name = None
    requires_permission = None

    """ Namespace for url. Can be left none. If not left none, know that url navigation will go like:
    committees:<namespace>:url_name
    """
    namespace = None

    def get_urls(self):
        """ Builds a URLconf.
        When defining the view classes make sure they implement this config. Eg:
        > path('url_path/', views.MyCommitteeTabView.as_view(config=MyCommitteeConfig))
        This way the AssociationGroupMixin checks if this tab is accessable for the particular group.
        """
        raise NotImplementedError

    @property
    def urls(self):
        return self.get_urls(), self.namespace, self.namespace

    def get_tab_data(self):
        """ This creates the data for tab display
        name: The display name
        tab_select_keyword: value that marks that this tab is selected
        url_name: name of the url. Url may only accept group_id as a kwarg.
        """
        return {
            'name': self.name,
            'tab_select_keyword': self.tab_select_keyword,
            'url_name': self.url_name,
        }

    @classmethod
    def is_valid_for_group(cls, association_group: AssociationGroup):
        """
        Checks for a given association_group is the group has access to this tab page.
        :param association_group: The association group
        :return: Boolean determining access
        """
        if cls.requires_permission is not None:
            app_label, codename = cls.requires_permission.split('.', maxsplit=1)
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


def get_all_configs():
    """ Returns a list of all committee page configs"""
    configs = []

    # Go over all registered apps and check if it has a committee_pages config
    for app in apps.get_app_configs():
        try:
            module = import_module(f'{app.name}.committee_pages.config')
        except ModuleNotFoundError:
            pass
        else:
            for name, cls in module.__dict__.items():
                if isinstance(cls, type):
                    # Get all subclasses of SetupConfig, but not accidental imported copies of CommitteeConfig
                    if issubclass(cls, CommitteeConfig) and cls != CommitteeConfig:
                        config = cls()  # Initialise config
                        configs.append(config)
    return configs

def get_all_configs_for_group(association_group):
    configs = []
    for committee_config in get_all_configs():
        if committee_config.is_valid_for_group(association_group):
            configs.append(committee_config)
    return configs
