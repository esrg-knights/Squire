from django.core.exceptions import PermissionDenied
from user_interaction.config import registry


class AccountViewMixin:
    """
    Mixin for Account Config classes
    """
    config = None
    selected_tab_name = None

    def dispatch(self, request, *args, **kwargs):
        if self.config is None:
            raise KeyError(f"{self.__class__.__name__} does not have a config linked did you forget to assign it "
                           f"in your urls in your config class? ({self.__class__.__name__}).as_view(config=self)")

        if not self.config.valid_for_request(request):
            raise PermissionDenied()

        return super(AccountViewMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super(AccountViewMixin, self).get_context_data(
            tabs=self.get_tabs(),
            **kwargs
        )

    def get_tabs(self):
        tabs = []
        for account_page_config in registry.get_applicable_configs(self.request):
            tabs.append({
                'name': account_page_config.tab_select_keyword,
                'verbose': account_page_config.name,
                'url_name': 'account:'+account_page_config.url_name,
                'selected': account_page_config.tab_select_keyword == self.config.tab_select_keyword,
            })
        return tabs
