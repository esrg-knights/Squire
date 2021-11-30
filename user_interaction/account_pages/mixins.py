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
        for member_page_config in get_all_configs():
            tabs.append({
                'name': member_page_config.tab_select_keyword,
                'verbose': member_page_config.name,
                'url_name': 'account:'+member_page_config.url_name,
                'selected': member_page_config.tab_select_keyword == self.selected_tab_name,
            })
        return tabs
