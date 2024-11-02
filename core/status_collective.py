from utils.viewcollectives import ViewCollectiveConfig, ViewCollectiveRegistry, ViewCollectiveViewMixin


class AdminStatusBaseConfig(ViewCollectiveConfig):
    """Configurations for additional tabs on committee pages"""

    url_keyword = None
    name = None
    url_name = None

    """ Namespace for url. Can be left none. If not left none, know that url navigation will go like:
    core:<namespace>:url_name
    """
    namespace = None

    def is_accessible_for(self, request) -> bool:
        return request.user.is_superuser


class AdminStatusViewMixin(ViewCollectiveViewMixin):
    """
    Mixin for Admin Status Config classes
    """

    pass


registry = ViewCollectiveRegistry("status", "admin_status", root_namespace="core", config_class=AdminStatusBaseConfig)
