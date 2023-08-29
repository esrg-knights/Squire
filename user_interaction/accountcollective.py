from utils.viewcollectives import ViewCollectiveConfig, ViewCollectiveRegistry, ViewCollectiveViewMixin


class AccountBaseConfig(ViewCollectiveConfig):
    """Configurations for additional tabs on user account-related pages"""

    # Variables for basic requirements
    requires_login = True
    requires_membership = True


class AccountViewMixin(ViewCollectiveViewMixin):
    """
    Mixin for Account Config classes
    """

    pass


registry = ViewCollectiveRegistry("account", "account_pages", config_class=AccountBaseConfig)
