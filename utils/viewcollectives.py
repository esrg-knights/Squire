from importlib import import_module
from django.apps import apps
from django.core.exceptions import PermissionDenied
from django.urls import reverse


__all__ = ['ViewCollectiveConfig', 'ViewCollectiveViewMixin', 'AccountRegistry']


class ViewCollectiveConfig:
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


class ViewCollectiveViewMixin:
    """
    Mixin for Account Config classes
    """
    config = None
    registry = None
    root_namespace = None

    def __init__(self, *args, config=None, **kwargs):
        self.config = config
        if self.config is None:
            raise KeyError(f"{self.__class__.__name__} does not have a config linked did you forget to assign it "
                           f"in your urls in your config class? ({self.__class__.__name__}).as_view(config=self)")

        super(ViewCollectiveViewMixin, self).__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        if not self._check_config_access():
            raise PermissionDenied()

        return super(ViewCollectiveViewMixin, self).dispatch(request, *args, **kwargs)

    def _check_config_access(self):
        """
         Checks whether the current session has permission.
         Override this in case checks uses other variables than request.
        :return: Boolean
        """
        return self.config.valid_for_request(request=self.request)

    def get_context_data(self, **kwargs):
        return super(ViewCollectiveViewMixin, self).get_context_data(
            tabs=self.get_tabs(),
            **kwargs
        )

    def get_tabs(self):
        tabs = []
        for account_page_config in self.registry.get_applicable_configs(self.request):
            tabs.append({
                'name': account_page_config.tab_select_keyword,
                'verbose': account_page_config.name,
                'url': self._get_tab_url(self.root_namespace+':'+account_page_config.url_name),
                'selected': account_page_config == self.config,
            })
        return tabs

    def _get_tab_url(self, url_name, **url_kwargs):
        """ Returns the url for the tab. Interject url_kwargs to add extra perameters"""
        return reverse(url_name, kwargs=url_kwargs)



class AccountRegistry:
    config_class = ViewCollectiveConfig

    def __init__(self, folder_name, config_class=None):
        self.folder_name = folder_name
        self.config_class = config_class or self.config_class
        self._configs = None

    def get_applicable_configs(self, request, **other_kwargs):
        """
        Returns a list of all applicable configs
        :param request: The request containing the user and member instances of the session
        :param other_kwargs: keyword arguments related to the sequence of configs as defined in related config class
        :return: List of applicable confis
        """
        applicable_configs = []
        for config in self.configs:
            if config.valid_for_request(request, **other_kwargs):
                applicable_configs.append(config)
        return applicable_configs

    @property
    def configs(self):
        """ Returns a list of all related collective configs"""
        if self._configs is None:
            self._configs = self._get_configs()
        return self._configs

    def _get_configs(self):
        """ Constructs a list of all related collective configs """
        configs = []

        # Go over all registered apps and check if it has a committee_pages config
        for app in apps.get_app_configs():
            try:
                module = import_module(f'{app.name}.{self.folder_name}.config')
            except ModuleNotFoundError:
                pass
            else:
                for name, cls in module.__dict__.items():
                    if isinstance(cls, type):
                        # Get all subclasses of SetupConfig, but not accidental imported copies of CommitteeConfig
                        if issubclass(cls, self.config_class) and cls != self.config_class:
                            config = cls()  # Initialise config
                            configs.append(config)
        return sorted(configs, key= lambda config: config.order_value)
