from functools import *
from importlib import import_module

from django.apps import apps


class AccountConfig:
    """ Configurations for additional tabs on membership pages """
    name = None
    tab_select_keyword = None
    url_name = None
    order_value = 10

    """ Namespace for url. Can be left none. If not left none, know that url navigation will go like:
    accounts:<namespace>:url_name
    """
    namespace = None

    # Variables for basic requirements
    requires_login = True
    requires_membership = True

    def valid_for_request(self, request):
        """ Determines whether the given request allows this"""
        if self.requires_login and not request.user.is_authenticated:
            return False
        if self.requires_membership and request.member is None:
            return False
        return True

    def get_urls(self):
        """ Builds a URLconf.
        When defining the view classes make sure they implement this config. Eg:
        > path('url_path/', views.MyMemberTabView.as_view(config=MyMemmberConfig))
        """
        raise NotImplementedError

    @property
    def urls(self):
        return self.get_urls(), self.namespace, self.namespace


class AccountRegistry:

    def get_applicable_configs(self, request):
        """
        Returns a list of all applicable configs
        :param request: The request containing the user and member instances of the session
        :return: List of applicable confis
        """
        applicable_configs = []
        for config in self.configs:
            if config.valid_for_request(request):
                applicable_configs.append(config)
        return applicable_configs


    @cached_property
    def configs(self):
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
        return sorted(configs, key= lambda config: config.order_value)

registry = AccountRegistry()
