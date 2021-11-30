from django.views.generic import TemplateView

from user_interaction.account_pages.mixins import AccountTabsMixin


class SiteAccountView(AccountTabsMixin, TemplateView):
    template_name = "user_interaction/site_account_page.html"
    selected_tab_name = 'tab_member_info'
