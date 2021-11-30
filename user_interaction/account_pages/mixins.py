from user_interaction.config import get_all_configs


class AccountTabsMixin:
    config_class = None
    selected_tab_name = None

    def get_context_data(self, **kwargs):
        return super(AccountTabsMixin, self).get_context_data(
            tabs=self.get_tabs(),
            **kwargs
        )

    def get_tabs(self):
        tabs = []
        for account_page_config in get_all_configs():
            tabs.append({
                'name': account_page_config.tab_select_keyword,
                'verbose': account_page_config.name,
                'url_name': 'account:'+account_page_config.url_name,
                'selected': account_page_config.tab_select_keyword == self.selected_tab_name,
            })
        return tabs
