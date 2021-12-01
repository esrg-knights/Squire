from utils.viewcollectives import ViewCollectiveConfig, AccountRegistry, ViewCollectiveViewMixin


class AccountConfig(ViewCollectiveConfig):
    """ Configurations for additional tabs on membership pages """
    # Variables for basic requirements
    requires_login = True
    requires_membership = True


class AccountViewMixin(ViewCollectiveViewMixin):
    """
    Mixin for Account Config classes
    """
    def __init__(self, *args, **kwargs):
        self.registry = registry
        super(AccountViewMixin, self).__init__(*args, **kwargs)


registry = AccountRegistry('account_pages', config_class=AccountConfig)

