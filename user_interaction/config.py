from importlib import import_module

from django.apps import apps


class AccountConfig:
    """ Configurations for additional tabs on membership pages """
    name = None
    tab_select_keyword = None
    url_name = None

    """ Namespace for url. Can be left none. If not left none, know that url navigation will go like:
    accounts:<namespace>:url_name
    """
    namespace = None

    def get_urls(self):
        """ Builds a URLconf.
        When defining the view classes make sure they implement this config. Eg:
        > path('url_path/', views.MyMemberTabView.as_view(config=MyMemmberConfig))
        """
        raise NotImplementedError

    @property
    def urls(self):
        return self.get_urls(), self.namespace, self.namespace


def get_all_configs():
    """ Returns a list of all committee page configs"""
    configs = []

    # Go over all registered apps and check if it has a committee_pages config
    for app in apps.get_app_configs():
        try:
            module = import_module(f'{app.name}.account_pages.config')
        except ModuleNotFoundError:
            pass
        else:
            for name, cls in module.__dict__.items():
                if isinstance(cls, type):
                    # Get all subclasses of SetupConfig, but not accidental imported copies of CommitteeConfig
                    if issubclass(cls, AccountConfig) and cls != AccountConfig:
                        config = cls()  # Initialise config
                        configs.append(config)
    return configs
