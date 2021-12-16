from django.urls import path

from user_interaction.accountcollective import AccountBaseConfig

from .views import SiteAccountView, AccountPasswordChangeView, LayoutPreferencesUpdateView, AccountChangeView


class AccountSettingsConfig(AccountBaseConfig):
    url_keyword = 'site'
    name = 'Account'
    url_name = 'site_account'
    order_value = 10  # Value determining the order of the tabs on the Account page

    requires_membership = False

    def get_urls(self):
        """ Builds a list of urls """
        return [
            path('', SiteAccountView.as_view(config=self), name='site_account'),
            path('change-password/', AccountPasswordChangeView.as_view(config=self), name='password_change'),
            path('change-layout/', LayoutPreferencesUpdateView.as_view(config=self), name='layout_change'),
            path('account/edit', AccountChangeView.as_view(config=self), name='account_change'),
        ]
